from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import openai
import pytest
from pydantic import BaseModel

from learnai.config import LLMTask, Settings
from learnai.errors import UpstreamError
from learnai.services.llm.openai_compat_client import OpenAICompatLLMClient


def _chat_completion(
    content: str | None, *, finish_reason: str = "stop", model: str = "test-model"
) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(finish_reason=finish_reason, message=SimpleNamespace(content=content))
        ],
        model=model,
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
    )


class Answer(BaseModel):
    value: str


@pytest.fixture
def settings() -> Settings:
    return Settings(
        google_client_id="test-client-id",
        session_secret="a-test-secret-at-least-32-bytes-long",
        llm_backend="openai_compatible",
        llm_base_url="http://localhost:1234/v1",
    )


def _fake_sdk_client(*responses: object) -> MagicMock:
    fake = MagicMock()
    fake.chat.completions.create = AsyncMock(
        side_effect=list(responses) if len(responses) > 1 else None,
        return_value=responses[0] if len(responses) == 1 else None,
    )
    return fake


async def test_complete_returns_text(settings: Settings) -> None:
    fake = _fake_sdk_client(_chat_completion("hello there"))
    client = OpenAICompatLLMClient(fake, settings)

    result = await client.complete(task=LLMTask.profile_description, prompt="hi")

    assert result == "hello there"


async def test_complete_raises_on_content_filter(settings: Settings) -> None:
    fake = _fake_sdk_client(_chat_completion(None, finish_reason="content_filter"))
    client = OpenAICompatLLMClient(fake, settings)

    with pytest.raises(UpstreamError, match="declined"):
        await client.complete(task=LLMTask.profile_description, prompt="hi")


async def test_complete_raises_on_empty_content(settings: Settings) -> None:
    fake = _fake_sdk_client(_chat_completion(""))
    client = OpenAICompatLLMClient(fake, settings)

    with pytest.raises(UpstreamError, match="empty response"):
        await client.complete(task=LLMTask.profile_description, prompt="hi")


async def test_structured_uses_native_schema_when_supported(settings: Settings) -> None:
    fake = _fake_sdk_client(_chat_completion('{"value": "ok"}'))
    client = OpenAICompatLLMClient(fake, settings)

    result = await client.structured(task=LLMTask.profile_description, prompt="hi", schema=Answer)

    assert result == Answer(value="ok")
    call_kwargs = fake.chat.completions.create.call_args.kwargs
    assert call_kwargs["response_format"]["type"] == "json_schema"


async def test_structured_falls_back_to_prompted_repair_when_native_fails(
    settings: Settings,
) -> None:
    # First call (native, response_format set) returns non-JSON content;
    # second call (prompted fallback) returns loosely-formed JSON that
    # json_repair can fix (single quotes, trailing comma).
    fake = _fake_sdk_client(_chat_completion("not json"), _chat_completion("{'value': 'ok',}"))
    client = OpenAICompatLLMClient(fake, settings)

    result = await client.structured(task=LLMTask.profile_description, prompt="hi", schema=Answer)

    assert result == Answer(value="ok")
    assert fake.chat.completions.create.await_count == 2


async def test_structured_skips_native_when_backend_does_not_support_it(
    settings: Settings,
) -> None:
    settings = settings.model_copy(update={"llm_supports_json_schema": False})
    fake = _fake_sdk_client(_chat_completion('{"value": "ok"}'))
    client = OpenAICompatLLMClient(fake, settings)

    result = await client.structured(task=LLMTask.profile_description, prompt="hi", schema=Answer)

    assert result == Answer(value="ok")
    assert fake.chat.completions.create.await_count == 1
    call_kwargs = fake.chat.completions.create.call_args.kwargs
    assert "response_format" not in call_kwargs


async def test_request_failure_is_wrapped_as_upstream_error(settings: Settings) -> None:
    request = httpx.Request("POST", "http://localhost:1234/v1/chat/completions")
    response = httpx.Response(status_code=500, request=request)
    fake = MagicMock()
    fake.chat.completions.create = AsyncMock(
        side_effect=openai.APIStatusError("server error", response=response, body=None)
    )
    client = OpenAICompatLLMClient(fake, settings)

    with pytest.raises(UpstreamError, match="request failed"):
        await client.complete(task=LLMTask.profile_description, prompt="hi")


async def test_connection_failure_is_wrapped_as_upstream_error(settings: Settings) -> None:
    request = httpx.Request("POST", "http://localhost:1234/v1/chat/completions")
    fake = MagicMock()
    fake.chat.completions.create = AsyncMock(side_effect=openai.APIConnectionError(request=request))
    client = OpenAICompatLLMClient(fake, settings)

    with pytest.raises(UpstreamError, match="connection failed"):
        await client.complete(task=LLMTask.profile_description, prompt="hi")
