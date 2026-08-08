"""Live contract tests for both LLM backends — the actual verification for
the plan's Phase 2 acceptance bar ("passes against both adapters"). The
unit tests in tests/unit/test_anthropic_llm_client.py and
test_openai_compat_llm_client.py cover request/response handling against
mocked SDK clients; these hit the real thing.

Marked ``live`` (see pyproject.toml) and deselected by default. Each test
additionally skips itself when the credential/endpoint it needs isn't
configured, so a bare ``pytest -m live`` run degrades to "skipped" rather
than "failed" in an environment missing one of the two backends. Run
explicitly:

    ANTHROPIC_API_KEY=... pytest -m live tests/contract/test_llm_adapters_live.py
    LLM_BASE_URL=http://localhost:1234/v1 pytest -m live tests/contract/test_llm_adapters_live.py
"""

from __future__ import annotations

import os

import anthropic
import openai
import pytest

from learnai.config import LLMTask, Settings
from learnai.services.llm.anthropic_client import AnthropicLLMClient
from learnai.services.llm.openai_compat_client import OpenAICompatLLMClient

pytestmark = pytest.mark.live

_PROMPT = "Reply with exactly the word: ok"

# tests/conftest.py sets this placeholder via os.environ.setdefault so the
# rest of the suite can construct Settings() without a real key — it must
# not be mistaken for a real credential here, or `-m live` would attempt a
# real request with a fake key and fail instead of skipping cleanly.
_PLACEHOLDER_ANTHROPIC_KEY = "test-key-not-real"


@pytest.mark.skipif(
    os.environ.get("ANTHROPIC_API_KEY", "") in ("", _PLACEHOLDER_ANTHROPIC_KEY),
    reason="no real ANTHROPIC_API_KEY set",
)
async def test_anthropic_adapter_completes_a_real_request() -> None:
    settings = Settings(
        google_client_id="live-test", session_secret="a-test-secret-at-least-32-bytes-long"
    )
    client = AnthropicLLMClient(anthropic.AsyncAnthropic(), settings)

    result = await client.complete(task=LLMTask.profile_description, prompt=_PROMPT)

    assert result.strip()


@pytest.mark.skipif(
    not os.environ.get("LLM_BASE_URL"),
    reason="no LLM_BASE_URL set (a local OpenAI-compatible endpoint — LM Studio, vLLM, Ollama)",
)
async def test_openai_compatible_adapter_completes_a_real_request() -> None:
    settings = Settings(
        google_client_id="live-test",
        session_secret="a-test-secret-at-least-32-bytes-long",
        llm_backend="openai_compatible",
        llm_base_url=os.environ["LLM_BASE_URL"],
        llm_model_default=os.environ.get("LLM_MODEL_DEFAULT", "local-model"),
    )
    sdk_client = openai.AsyncOpenAI(
        api_key=settings.generation_api_key() or "not-needed", base_url=settings.llm_base_url
    )
    client = OpenAICompatLLMClient(sdk_client, settings)

    result = await client.complete(task=LLMTask.profile_description, prompt=_PROMPT)

    assert result.strip()
