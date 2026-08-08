"""Settings: dev defaults work with nothing set, prod guards actually fire."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from learnai.config import Environment, LLMTask, Settings


def test_dev_defaults_require_no_configuration() -> None:
    settings = Settings(_env_file=None)
    assert settings.environment is Environment.development
    assert settings.model_for(LLMTask.narrative) == settings.llm_model_default


def test_max_tokens_override_applies_per_task() -> None:
    settings = Settings(_env_file=None)
    assert settings.max_tokens_for(LLMTask.narrative) == 16_000
    assert settings.max_tokens_for(LLMTask.profile_description) == 1_000


def test_effort_override_applies_to_game_code() -> None:
    settings = Settings(_env_file=None)
    assert settings.effort_for(LLMTask.game_code) == "xhigh"
    assert settings.effort_for(LLMTask.narrative) == settings.llm_effort_default


def test_generation_api_key_falls_back_to_anthropic_key() -> None:
    settings = Settings(_env_file=None, anthropic_api_key="sk-ant-fake")
    assert settings.generation_api_key() == "sk-ant-fake"


def test_generation_api_key_prefers_dedicated_key() -> None:
    settings = Settings(
        _env_file=None,
        anthropic_api_key="sk-ant-fake",
        llm_backend="openai_compatible",
        llm_base_url="http://localhost:1234/v1",
        llm_api_key="sk-openrouter-fake",
    )
    assert settings.generation_api_key() == "sk-openrouter-fake"


@pytest.mark.parametrize(
    "overrides",
    [
        {},  # nothing set at all
        {"cors_origins": ["https://example.com"]},  # missing secret/keys
    ],
)
def test_production_without_required_config_fails_fast(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="invalid production configuration"):
        Settings(_env_file=None, environment=Environment.production, **overrides)


def test_production_with_openai_backend_requires_base_url() -> None:
    with pytest.raises(ValidationError, match="llm_base_url"):
        Settings(
            _env_file=None,
            environment=Environment.production,
            llm_backend="openai_compatible",
            anthropic_api_key="sk-ant-fake",
            google_client_id="fake",
            session_secret="x" * 32,
            cors_origins=["https://example.com"],
        )


def test_production_refuses_dev_auth_bypass() -> None:
    with pytest.raises(ValidationError, match="dev_auth_bypass"):
        Settings(
            _env_file=None,
            environment=Environment.production,
            dev_auth_bypass=True,
            anthropic_api_key="sk-ant-fake",
            google_client_id="fake",
            session_secret="x" * 32,
            cors_origins=["https://example.com"],
        )


def test_fully_configured_production_settings_succeed() -> None:
    settings = Settings(
        _env_file=None,
        environment=Environment.production,
        anthropic_api_key="sk-ant-fake",
        google_client_id="fake-client-id",
        session_secret="x" * 32,
        cors_origins=["https://example.com"],
    )
    assert settings.environment is Environment.production
