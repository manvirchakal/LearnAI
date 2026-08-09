from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import anthropic
import httpx
import pytest
from pydantic import BaseModel

from learnai.config import LLMTask, Settings
from learnai.errors import UpstreamError
from learnai.services.llm.anthropic_client import AnthropicLLMClient, _wrap_tool
from learnai.services.llm.client import AgentTool, AgentToolCall


class _FakeStream:
    """Mimics the async-context-manager returned by ``client.messages.stream``."""

    def __init__(self, message: object, *, chunks: list[str] | None = None) -> None:
        self._message = message
        # Assigned once, like the real SDK's own AsyncMessageStream — an
        # async generator object, consumed with `async for text in
        # stream.text_stream`.
        self.text_stream = self._make_text_stream(chunks or [])

    async def __aenter__(self) -> _FakeStream:
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def get_final_message(self) -> object:
        return self._message

    @staticmethod
    async def _make_text_stream(chunks: list[str]) -> Any:
        for chunk in chunks:
            yield chunk


def _text_message(
    text: str, *, stop_reason: str = "end_turn", model: str = "claude-opus-5"
) -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=text)],
        model=model,
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )


def _beta_message(
    text: str, *, stop_reason: str = "end_turn", role: str = "assistant"
) -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason=stop_reason,
        role=role,
        content=[SimpleNamespace(type="text", text=text)],
        model="claude-opus-5",
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )


class _FakeToolRunner:
    """Mimics ``client.beta.messages.tool_runner``'s async-iterable shape:
    ``async for message in runner`` plus ``generate_tool_call_response()``
    called once per yielded message — exactly the two operations
    ``AnthropicLLMClient._agent_once`` uses to mirror history."""

    def __init__(
        self, messages: list[SimpleNamespace], tool_responses: list[dict[str, Any] | None]
    ) -> None:
        self._messages = messages
        self._tool_responses = tool_responses
        self._index = 0

    def __aiter__(self) -> _FakeToolRunner:
        return self

    async def __anext__(self) -> SimpleNamespace:
        if self._index >= len(self._messages):
            raise StopAsyncIteration
        message = self._messages[self._index]
        self._index += 1
        return message

    async def generate_tool_call_response(self) -> dict[str, Any] | None:
        return self._tool_responses[self._index - 1]


class Answer(BaseModel):
    value: str


class SearchArgs(BaseModel):
    query: str


@pytest.fixture
def settings() -> Settings:
    return Settings(
        anthropic_api_key="sk-test",
        google_client_id="test-client-id",
        session_secret="a-test-secret-at-least-32-bytes-long",
    )


def _client_returning(
    message: object, settings: Settings, *, chunks: list[str] | None = None
) -> AnthropicLLMClient:
    fake_sdk_client = MagicMock()
    fake_sdk_client.messages.stream.return_value = _FakeStream(message, chunks=chunks)
    return AnthropicLLMClient(fake_sdk_client, settings)


async def test_complete_returns_text(settings: Settings) -> None:
    client = _client_returning(_text_message("hello there"), settings)

    result = await client.complete(task=LLMTask.profile_description, prompt="hi")

    assert result == "hello there"


async def test_complete_raises_on_refusal(settings: Settings) -> None:
    client = _client_returning(_text_message("", stop_reason="refusal"), settings)

    with pytest.raises(UpstreamError, match="declined"):
        await client.complete(task=LLMTask.profile_description, prompt="hi")


async def test_complete_raises_when_response_has_no_text_block(settings: Settings) -> None:
    message = SimpleNamespace(
        stop_reason="end_turn",
        content=[],
        model="claude-opus-5",
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
    )
    client = _client_returning(message, settings)

    with pytest.raises(UpstreamError, match="no text block"):
        await client.complete(task=LLMTask.profile_description, prompt="hi")


async def test_structured_parses_json_into_schema(settings: Settings) -> None:
    client = _client_returning(_text_message('{"value": "ok"}'), settings)

    result = await client.structured(task=LLMTask.profile_description, prompt="hi", schema=Answer)

    assert result == Answer(value="ok")


async def test_structured_raises_on_invalid_json(settings: Settings) -> None:
    client = _client_returning(_text_message("not json"), settings)

    with pytest.raises(UpstreamError, match="invalid structured output"):
        await client.structured(task=LLMTask.profile_description, prompt="hi", schema=Answer)


async def test_request_failure_is_wrapped_as_upstream_error(settings: Settings) -> None:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status_code=500, request=request)

    def _raise(*args: Any, **kwargs: Any) -> None:
        raise anthropic.APIStatusError("server error", response=response, body=None)

    fake_sdk_client = MagicMock()
    fake_sdk_client.messages.stream.side_effect = _raise
    client = AnthropicLLMClient(fake_sdk_client, settings)

    with pytest.raises(UpstreamError, match="Anthropic request failed"):
        await client.complete(task=LLMTask.profile_description, prompt="hi")


async def test_connection_failure_is_wrapped_as_upstream_error(settings: Settings) -> None:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")

    def _raise(*args: Any, **kwargs: Any) -> None:
        raise anthropic.APIConnectionError(request=request)

    fake_sdk_client = MagicMock()
    fake_sdk_client.messages.stream.side_effect = _raise
    client = AnthropicLLMClient(fake_sdk_client, settings)

    with pytest.raises(UpstreamError, match="Anthropic connection failed"):
        await client.complete(task=LLMTask.profile_description, prompt="hi")


async def test_stream_yields_deltas_in_order(settings: Settings) -> None:
    message = _text_message("irrelevant — text_stream is what's consumed")
    client = _client_returning(message, settings, chunks=["Once ", "upon ", "a time"])

    chunks = [chunk async for chunk in client.stream(task=LLMTask.narrative, prompt="hi")]

    assert chunks == ["Once ", "upon ", "a time"]


async def test_stream_raises_on_refusal_after_yielding_nothing(settings: Settings) -> None:
    message = _text_message("", stop_reason="refusal")
    client = _client_returning(message, settings, chunks=[])

    with pytest.raises(UpstreamError, match="declined"):
        async for _ in client.stream(task=LLMTask.narrative, prompt="hi"):
            pass


async def test_stream_request_failure_is_wrapped_as_upstream_error(settings: Settings) -> None:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status_code=500, request=request)

    def _raise(*args: Any, **kwargs: Any) -> None:
        raise anthropic.APIStatusError("server error", response=response, body=None)

    fake_sdk_client = MagicMock()
    fake_sdk_client.messages.stream.side_effect = _raise
    client = AnthropicLLMClient(fake_sdk_client, settings)

    with pytest.raises(UpstreamError, match="Anthropic request failed"):
        async for _ in client.stream(task=LLMTask.narrative, prompt="hi"):
            pass


async def test_wrap_tool_validates_arguments_and_records_the_call() -> None:
    calls: list[str] = []

    async def handler(query: str) -> str:
        calls.append(query)
        return f"found: {query}"

    tool = AgentTool(
        name="search", description="search stuff", args_schema=SearchArgs, handler=handler
    )
    tool_calls: list[AgentToolCall] = []
    runnable = _wrap_tool(tool, tool_calls)

    result = await runnable.call({"query": "derivatives"})

    assert result == "found: derivatives"
    assert calls == ["derivatives"]
    assert tool_calls == [
        AgentToolCall(
            tool_name="search", arguments={"query": "derivatives"}, result="found: derivatives"
        )
    ]


async def test_agent_returns_final_text_with_no_tool_calls(settings: Settings) -> None:
    fake_sdk_client = MagicMock()
    fake_sdk_client.beta.messages.tool_runner.return_value = _FakeToolRunner(
        [_beta_message("The answer is 42.")], [None]
    )
    client = AnthropicLLMClient(fake_sdk_client, settings)

    result = await client.agent(
        task=LLMTask.chat, system="sys", messages=[{"role": "user", "content": "hi"}], tools=[]
    )

    assert result.text == "The answer is 42."
    assert result.tool_calls == []


async def test_agent_raises_on_refusal(settings: Settings) -> None:
    fake_sdk_client = MagicMock()
    fake_sdk_client.beta.messages.tool_runner.return_value = _FakeToolRunner(
        [_beta_message("", stop_reason="refusal")], [None]
    )
    client = AnthropicLLMClient(fake_sdk_client, settings)

    with pytest.raises(UpstreamError, match="declined"):
        await client.agent(
            task=LLMTask.chat, system="sys", messages=[{"role": "user", "content": "hi"}], tools=[]
        )


async def test_agent_restarts_with_mirrored_history_after_pause_turn(settings: Settings) -> None:
    """The exact gotcha the tool_runner's Python implementation has: a
    pause_turn with no tool_use silently ends iteration. This asserts the
    documented fix — mirror history, start a *new* runner — actually
    happens rather than truncating the answer."""
    paused = _beta_message("partial answer, still thinking...", stop_reason="pause_turn")
    final = _beta_message("The complete answer.", stop_reason="end_turn")

    fake_sdk_client = MagicMock()
    fake_sdk_client.beta.messages.tool_runner.side_effect = [
        _FakeToolRunner([paused], [None]),
        _FakeToolRunner([final], [None]),
    ]
    client = AnthropicLLMClient(fake_sdk_client, settings)

    result = await client.agent(
        task=LLMTask.chat, system="sys", messages=[{"role": "user", "content": "hi"}], tools=[]
    )

    assert result.text == "The complete answer."
    assert fake_sdk_client.beta.messages.tool_runner.call_count == 2
    restart_messages = fake_sdk_client.beta.messages.tool_runner.call_args_list[1].kwargs[
        "messages"
    ]
    assert restart_messages[-1] == {"role": "assistant", "content": paused.content}


async def test_agent_gives_up_after_max_pause_turn_restarts(settings: Settings) -> None:
    always_paused = _beta_message("still going...", stop_reason="pause_turn")
    fake_sdk_client = MagicMock()
    fake_sdk_client.beta.messages.tool_runner.side_effect = [
        _FakeToolRunner([always_paused], [None]) for _ in range(10)
    ]
    client = AnthropicLLMClient(fake_sdk_client, settings)

    result = await client.agent(
        task=LLMTask.chat, system="sys", messages=[{"role": "user", "content": "hi"}], tools=[]
    )

    assert result.text == "still going..."
    assert fake_sdk_client.beta.messages.tool_runner.call_count == 4  # _MAX_PAUSE_TURN_RESTARTS + 1
