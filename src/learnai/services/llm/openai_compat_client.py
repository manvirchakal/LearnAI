"""OpenAI-Chat-Completions-compatible adapter — any endpoint that speaks that
wire format: OpenRouter, LM Studio, vLLM, Ollama, or a future local model.

Feature parity with the Anthropic adapter is graceful degradation, not a
hard requirement: local and third-party backends don't reliably guarantee
JSON-schema-constrained output the way Anthropic's ``output_config.format``
does. ``structured()`` tries the backend's native schema constraint first
when ``settings.llm_supports_json_schema`` says the backend advertises
support; on failure (or when it doesn't) it falls back to prompted JSON
plus repair via ``json_repair`` rather than refusing to run.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, TypeVar

import json_repair
import openai
import structlog
from pydantic import BaseModel

from learnai.config import LLMTask, Settings
from learnai.errors import UpstreamError
from learnai.services.llm.client import AgentResult, AgentTool, AgentToolCall

BaseModelT = TypeVar("BaseModelT", bound=BaseModel)

logger = structlog.get_logger(__name__)

Message = dict[str, str]


def _tool_def(tool: AgentTool) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.args_schema.model_json_schema(),
        },
    }


class OpenAICompatLLMClient:
    def __init__(self, client: openai.AsyncOpenAI, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def complete(self, *, task: LLMTask, prompt: str, system: str | None = None) -> str:
        response = await self._create(task, self._messages(system, prompt))
        return self._text(task, response)

    async def structured(
        self, *, task: LLMTask, prompt: str, schema: type[BaseModelT], system: str | None = None
    ) -> BaseModelT:
        messages = self._messages(system, prompt)
        if self._settings.llm_supports_json_schema:
            try:
                return await self._structured_native(task, messages, schema)
            except UpstreamError:
                logger.info(
                    "llm_structured_native_failed_falling_back",
                    backend="openai_compatible",
                    task=task,
                )
        return await self._structured_prompted(task, messages, schema)

    async def _structured_native(
        self, task: LLMTask, messages: list[Message], schema: type[BaseModelT]
    ) -> BaseModelT:
        response = await self._create(
            task,
            messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                    "strict": True,
                },
            },
        )
        text = self._text(task, response)
        try:
            return schema.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValueError) as exc:
            raise UpstreamError(f"native structured output failed for task {task}") from exc

    async def _structured_prompted(
        self, task: LLMTask, messages: list[Message], schema: type[BaseModelT]
    ) -> BaseModelT:
        schema_json = json.dumps(schema.model_json_schema())
        prompted = [
            *messages[:-1],
            {
                **messages[-1],
                "content": (
                    f"{messages[-1]['content']}\n\n"
                    "Respond with ONLY valid JSON matching this schema, no other text, "
                    f"no markdown fences:\n{schema_json}"
                ),
            },
        ]
        response = await self._create(task, prompted)
        text = self._text(task, response)
        repaired = json_repair.loads(text)
        try:
            return schema.model_validate(repaired)
        except ValueError as exc:
            raise UpstreamError(f"could not parse structured output for task {task}") from exc

    def stream(
        self, *, task: LLMTask, prompt: str, system: str | None = None
    ) -> AsyncIterator[str]:
        return self._stream_text(task, self._messages(system, prompt))

    async def _stream_text(self, task: LLMTask, messages: list[Message]) -> AsyncIterator[str]:
        # Unlike _create(), no token-usage log here: getting usage on a
        # streamed Chat Completions response needs `stream_options={
        # "include_usage": True}`, support for which isn't universal across
        # OpenAI-compatible backends. One more spot this adapter simply does
        # less than the Anthropic one, per this module's docstring.
        try:
            chunks = await self._client.chat.completions.create(
                model=self._settings.model_for(task),
                max_tokens=self._settings.max_tokens_for(task),
                messages=messages,  # type: ignore[arg-type]
                stream=True,
            )
            # The `messages=` shape mismatch below (same as _create()) makes
            # mypy's overload resolution fall back to the full
            # ChatCompletion | AsyncStream[ChatCompletionChunk] union rather
            # than picking the stream=True overload.
            async for chunk in chunks:  # type: ignore[union-attr]
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except openai.APIStatusError as exc:
            raise UpstreamError(
                f"{self._settings.llm_backend} request failed for task {task}: {exc.message}"
            ) from exc
        except openai.APIConnectionError as exc:
            raise UpstreamError(
                f"{self._settings.llm_backend} connection failed for task {task}"
            ) from exc

    async def agent(
        self,
        *,
        task: LLMTask,
        system: str,
        messages: list[dict[str, str]],
        tools: list[AgentTool],
        max_iterations: int = 8,
    ) -> AgentResult:
        """A manual tool-call loop over Chat Completions ``tools``/
        ``tool_choice`` — the graceful-degradation counterpart to the
        Anthropic adapter's ``client.beta.messages.tool_runner``. No
        ``pause_turn`` equivalent exists in this API: the loop only ever
        ends on a response with no ``tool_calls``, or on ``max_iterations``.
        """
        tool_by_name = {tool.name: tool for tool in tools}
        tool_defs = [_tool_def(tool) for tool in tools]
        tool_calls: list[AgentToolCall] = []

        chat_messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
        chat_messages.extend({"role": m["role"], "content": m["content"]} for m in messages)

        for _ in range(max_iterations):
            response = await self._create(task, chat_messages, tools=tool_defs)
            message = response.choices[0].message

            if not message.tool_calls:
                return AgentResult(text=self._text(task, response), tool_calls=tool_calls)

            # Every tool we declare is type="function" (see _tool_def), so
            # the model only ever emits function tool calls back — the
            # union with "custom" tool calls in the SDK's type is for a
            # feature we never enable.
            calls = [call for call in message.tool_calls if call.type == "function"]
            chat_messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        }
                        for call in calls
                    ],
                }
            )
            for call in calls:
                result = await self._run_tool(tool_by_name, call, tool_calls)
                chat_messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

        raise UpstreamError(
            f"{self._settings.llm_backend} agent exceeded max_iterations for task {task}"
        )

    async def _run_tool(
        self,
        tool_by_name: dict[str, AgentTool],
        call: openai.types.chat.ChatCompletionMessageFunctionToolCall,
        tool_calls: list[AgentToolCall],
    ) -> str:
        """Executes one tool call, catching everything — a malformed
        argument or a failing tool becomes error text fed back to the
        model, not a crashed request. Mirrors how the Anthropic SDK's
        ``tool_runner`` itself handles both an unknown tool name and a
        tool that raises (see ``anthropic.lib.tools._tool_dispatch``)."""
        tool = tool_by_name.get(call.function.name)
        if tool is None:
            return f"Error: Tool '{call.function.name}' not found"
        try:
            arguments = tool.args_schema.model_validate_json(call.function.arguments).model_dump(
                mode="json"
            )
            result = await tool.handler(**arguments)
        except Exception as exc:  # noqa: BLE001 - fed back to the model as tool output, not raised
            return f"Error: {exc}"
        tool_calls.append(AgentToolCall(tool_name=tool.name, arguments=arguments, result=result))
        return result

    async def _create(
        self,
        task: LLMTask,
        messages: list[dict[str, Any]],
        *,
        response_format: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> openai.types.chat.ChatCompletion:
        kwargs: dict[str, Any] = {}
        if response_format is not None:
            kwargs["response_format"] = response_format
        if tools is not None:
            kwargs["tools"] = tools
        try:
            response = await self._client.chat.completions.create(
                model=self._settings.model_for(task),
                max_tokens=self._settings.max_tokens_for(task),
                messages=messages,  # type: ignore[arg-type]
                **kwargs,
            )
        except openai.APIStatusError as exc:
            raise UpstreamError(
                f"{self._settings.llm_backend} request failed for task {task}: {exc.message}"
            ) from exc
        except openai.APIConnectionError as exc:
            raise UpstreamError(
                f"{self._settings.llm_backend} connection failed for task {task}"
            ) from exc

        logger.info(
            "llm_completion",
            backend=self._settings.llm_backend,
            task=task,
            model=response.model,
            input_tokens=response.usage.prompt_tokens if response.usage else None,
            output_tokens=response.usage.completion_tokens if response.usage else None,
        )
        return response

    def _text(self, task: LLMTask, response: openai.types.chat.ChatCompletion) -> str:
        choice = response.choices[0]
        if choice.finish_reason == "content_filter":
            raise UpstreamError(
                f"{self._settings.llm_backend} declined the request for task {task}"
            )
        content = choice.message.content
        if not content:
            raise UpstreamError(
                f"{self._settings.llm_backend} returned an empty response for task {task}"
            )
        return content

    def _messages(self, system: str | None, prompt: str) -> list[Message]:
        messages: list[Message] = []
        if system is not None:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages
