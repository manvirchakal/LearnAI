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
from typing import Any, TypeVar

import anthropic
import structlog
from anthropic.lib.tools import BetaAsyncFunctionTool, beta_async_tool
from pydantic import BaseModel

from learnai.config import LLMTask, Settings
from learnai.errors import UpstreamError
from learnai.services.llm.client import AgentResult, AgentTool, AgentToolCall

BaseModelT = TypeVar("BaseModelT", bound=BaseModel)

logger = structlog.get_logger(__name__)

# Cap on client.beta.messages.tool_runner restarts after a pause_turn.
# The Python tool runner does NOT auto-resume a paused turn — it only
# continues the loop on tool_use; a pause_turn with no tool_use silently
# ends iteration with a truncated answer (see _agent_once's docstring).
# This bounds how many times we restart a fresh runner with the mirrored
# history before giving up, mirroring the "max_continuations" advice for
# this exact mechanic.
_MAX_PAUSE_TURN_RESTARTS = 3


def _wrap_tool(tool: AgentTool, tool_calls: list[AgentToolCall]) -> BetaAsyncFunctionTool[Any]:
    """Adapts our backend-agnostic ``AgentTool`` into a ``tool_runner``-
    runnable one. Real argument validation happens here against ``tool.
    args_schema`` — the tool function itself is declared ``**kwargs: Any``,
    so ``pydantic.validate_call`` (which ``beta_async_tool`` wraps every
    tool function in) does no useful validation on its own. Every call is
    also recorded into ``tool_calls`` so the caller can build citations
    from ``search_materials`` invocations after the loop ends.
    """

    async def _run(**kwargs: Any) -> str:
        validated = tool.args_schema.model_validate(kwargs)
        arguments = validated.model_dump(mode="json")
        result = await tool.handler(**arguments)
        tool_calls.append(AgentToolCall(tool_name=tool.name, arguments=arguments, result=result))
        return result

    return beta_async_tool(
        _run, name=tool.name, description=tool.description, input_schema=tool.args_schema
    )


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

    async def agent(
        self,
        *,
        task: LLMTask,
        system: str,
        messages: list[dict[str, str]],
        tools: list[AgentTool],
        max_iterations: int = 8,
    ) -> AgentResult:
        tool_calls: list[AgentToolCall] = []
        runnable_tools = [_wrap_tool(tool, tool_calls) for tool in tools]

        history: list[dict[str, Any]] = [dict(m) for m in messages]
        last_message = None
        for _ in range(_MAX_PAUSE_TURN_RESTARTS + 1):
            last_message, history = await self._agent_once(
                task=task,
                system=system,
                history=history,
                runnable_tools=runnable_tools,
                max_iterations=max_iterations,
            )
            if last_message.stop_reason != "pause_turn":
                break
            logger.info("llm_agent_pause_turn_restart", task=task)

        if (
            last_message is None
        ):  # pragma: no cover - range(_MAX_PAUSE_TURN_RESTARTS + 1) always runs
            raise UpstreamError(f"Anthropic agent loop produced no response for task {task}")
        if last_message.stop_reason == "refusal":
            raise UpstreamError(f"Anthropic declined the request for task {task}")

        logger.info(
            "llm_completion",
            backend="anthropic",
            task=task,
            model=last_message.model,
            input_tokens=last_message.usage.input_tokens,
            output_tokens=last_message.usage.output_tokens,
            agent=True,
            tool_calls=len(tool_calls),
        )
        return AgentResult(text=self._beta_text(task, last_message), tool_calls=tool_calls)

    async def _agent_once(
        self,
        *,
        task: LLMTask,
        system: str,
        history: list[dict[str, Any]],
        runnable_tools: list[BetaAsyncFunctionTool[Any]],
        max_iterations: int,
    ) -> tuple[anthropic.types.beta.BetaMessage, list[dict[str, Any]]]:
        """Runs one ``tool_runner`` to completion and returns its final
        message plus a locally-mirrored copy of the full message history.

        The mirror exists because ``tool_runner`` does not expose its
        internal message list, and — critically — does not auto-resume a
        ``pause_turn`` (a turn that ends without a ``tool_use`` block after
        running long still stops the loop, since ``generate_tool_call_
        response()`` finds no tool_use to act on and returns ``None``). The
        caller restarts a *new* runner from this mirror when that happens,
        exactly the "mirror history and restart" pattern the SDK docs
        prescribe for this mechanic.
        """
        try:
            runner = self._client.beta.messages.tool_runner(
                model=self._settings.model_for(task),
                max_tokens=self._settings.max_tokens_for(task),
                system=system,
                messages=history,  # type: ignore[arg-type]
                tools=runnable_tools,
                max_iterations=max_iterations,
            )
            mirror = list(history)
            last_message = None
            async for message in runner:
                mirror.append({"role": message.role, "content": message.content})
                tool_response = await runner.generate_tool_call_response()
                if tool_response is not None:
                    mirror.append(tool_response)  # type: ignore[arg-type]
                last_message = message
        except anthropic.APIStatusError as exc:
            raise UpstreamError(f"Anthropic request failed for task {task}: {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise UpstreamError(f"Anthropic connection failed for task {task}") from exc

        if last_message is None:  # pragma: no cover - tool_runner always yields at least once
            raise UpstreamError(f"Anthropic agent loop produced no response for task {task}")
        return last_message, mirror

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

    def _beta_text(self, task: LLMTask, message: anthropic.types.beta.BetaMessage) -> str:
        # Same shape as _text, but for the beta message type tool_runner
        # returns — the two aren't the same class, so this can't just
        # reuse _text despite being otherwise identical.
        for block in message.content:
            if block.type == "text":
                return block.text
        raise UpstreamError(f"Anthropic agent response for task {task} contained no text block")
