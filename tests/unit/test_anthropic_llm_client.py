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
from learnai.services.llm.anthropic_client import AnthropicLLMClient


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


class Answer(BaseModel):
    value: str


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
