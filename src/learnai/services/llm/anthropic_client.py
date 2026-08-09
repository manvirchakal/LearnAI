"""Anthropic adapter for ``LLMClient`` — the default generation backend,
also used whenever ``settings.llm_backend == "anthropic"``.

Always streams, even for short completions: the SDK refuses large
non-streaming requests outright (they'd risk an HTTP timeout), and using
one code path for every task size means this client doesn't need to
special-case task budgets later. No ``temperature``/``top_p``/``top_k`` are
ever set — current Claude models (Opus 5 and later) reject them outright;
steer via prompting instead. Thinking is left unset so it runs adaptive on
models that support it and is simply absent on ones that don't.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import TypeVar

import anthropic
import structlog
from pydantic import BaseModel

from learnai.config import LLMTask, Settings
from learnai.errors import UpstreamError

BaseModelT = TypeVar("BaseModelT", bound=BaseModel)

logger = structlog.get_logger(__name__)


class AnthropicLLMClient:
    def __init__(self, client: anthropic.AsyncAnthropic, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def complete(self, *, task: LLMTask, prompt: str, system: str | None = None) -> str:
        message = await self._create(task=task, prompt=prompt, system=system)
        return self._text(task, message)

    async def structured(
        self, *, task: LLMTask, prompt: str, schema: type[BaseModelT], system: str | None = None
    ) -> BaseModelT:
        message = await self._create(
            task=task,
            prompt=prompt,
            system=system,
            output_format={"type": "json_schema", "schema": schema.model_json_schema()},
        )
        text = self._text(task, message)
        try:
            return schema.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValueError) as exc:
            raise UpstreamError(f"Anthropic returned invalid structured output for {task}") from exc

    def stream(
        self, *, task: LLMTask, prompt: str, system: str | None = None
    ) -> AsyncIterator[str]:
        return self._stream_text(task=task, prompt=prompt, system=system)

    async def _stream_text(
        self, *, task: LLMTask, prompt: str, system: str | None
    ) -> AsyncIterator[str]:
        kwargs: dict[str, object] = {}
        if system is not None:
            kwargs["system"] = system

        try:
            async with self._client.messages.stream(
                model=self._settings.model_for(task),
                max_tokens=self._settings.max_tokens_for(task),
                messages=[{"role": "user", "content": prompt}],
                output_config={"effort": self._settings.effort_for(task)},  # type: ignore[arg-type]
                **kwargs,  # type: ignore[arg-type]
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                message = await stream.get_final_message()
        except anthropic.APIStatusError as exc:
            raise UpstreamError(f"Anthropic request failed for task {task}: {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise UpstreamError(f"Anthropic connection failed for task {task}") from exc

        # A refusal (rare, and typically with no text emitted beforehand —
        # the model declines outright rather than partially answering) is
        # only knowable from the final message, after every delta above has
        # already been yielded. The caller (the SSE endpoint) is what turns
        # this into a client-visible error event appended to the stream.
        if message.stop_reason == "refusal":
            raise UpstreamError(f"Anthropic declined the request for task {task}")

        logger.info(
            "llm_completion",
            backend="anthropic",
            task=task,
            model=message.model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            streamed=True,
        )

    async def _create(
        self,
        *,
        task: LLMTask,
        prompt: str,
        system: str | None,
        output_format: dict[str, object] | None = None,
    ) -> anthropic.types.Message:
        output_config: dict[str, object] = {"effort": self._settings.effort_for(task)}
        if output_format is not None:
            output_config["format"] = output_format
        kwargs: dict[str, object] = {}
        if system is not None:
            kwargs["system"] = system

        try:
            async with self._client.messages.stream(
                model=self._settings.model_for(task),
                max_tokens=self._settings.max_tokens_for(task),
                messages=[{"role": "user", "content": prompt}],
                output_config=output_config,  # type: ignore[arg-type]
                **kwargs,  # type: ignore[arg-type]
            ) as stream:
                message = await stream.get_final_message()
        except anthropic.APIStatusError as exc:
            raise UpstreamError(f"Anthropic request failed for task {task}: {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise UpstreamError(f"Anthropic connection failed for task {task}") from exc

        logger.info(
            "llm_completion",
            backend="anthropic",
            task=task,
            model=message.model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )
        return message

    def _text(self, task: LLMTask, message: anthropic.types.Message) -> str:
        if message.stop_reason == "refusal":
            raise UpstreamError(f"Anthropic declined the request for task {task}")
        for block in message.content:
            if block.type == "text":
                return block.text
        raise UpstreamError(f"Anthropic response for task {task} contained no text block")
