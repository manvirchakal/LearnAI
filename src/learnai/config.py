"""Application configuration.

Every environment variable the app reads is declared here, typed, and validated at
startup. Two things this deliberately fixes from the old ``server/main.py``:

* Nothing is read at import time. The old module fetched Cognito JWKS on import
  (``main.py:154``), so the process could not start without network access.
* Region and origin values are no longer hardcoded. The old code pinned some AWS
  clients to ``us-east-1``, gave others no region at all, and froze CORS to
  ``http://localhost:3000``.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    development = "development"
    test = "test"
    production = "production"


class LLMTask(StrEnum):
    """Every distinct call we make to the model.

    Each task gets its own model/effort/token budget so cost can be tuned per
    workload without touching call sites. They all default to the same model;
    tier them down only against measured numbers.
    """

    profile_description = "profile_description"
    toc = "toc"
    section_extraction = "section_extraction"
    narrative = "narrative"
    game_idea = "game_idea"
    game_code = "game_code"
    diagrams = "diagrams"
    chat = "chat"
    translation = "translation"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Environment = Environment.development

    # --- datastores ---------------------------------------------------------
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "learnai"
    qdrant_url: str = "http://localhost:6333"
    redis_url: str = "redis://localhost:6379"

    # --- blob storage -------------------------------------------------------
    # "local" writes to storage_root, which is a PVC mount in Kubernetes.
    # "minio" is the escape hatch for clusters without a ReadWriteMany
    # StorageClass, where API and worker cannot share a filesystem.
    storage_backend: Literal["local", "minio"] = "local"
    storage_root: Path = Path("/data/media")
    minio_endpoint: str | None = None
    minio_access_key: SecretStr | None = None
    minio_secret_key: SecretStr | None = None
    minio_bucket: str = "learnai"

    # --- llm: ingestion (always Anthropic — native PDF document blocks, ------
    # citations, and the Files API have no OpenAI-compatible equivalent) -----
    anthropic_api_key: SecretStr = SecretStr("")

    # --- llm: generation (narrative, game idea/code, diagrams, chat, --------
    # translation) — provider-agnostic. "anthropic" reuses anthropic_api_key ---
    # above; "openai_compatible" points the openai SDK at any base_url that ---
    # speaks the Chat Completions API: OpenRouter, LM Studio, vLLM, Ollama. ---
    llm_backend: Literal["anthropic", "openai_compatible"] = "anthropic"
    llm_base_url: str | None = None  # required when llm_backend != "anthropic"
    llm_api_key: SecretStr | None = None  # falls back to anthropic_api_key
    # Whether the configured backend advertises support for constrained JSON
    # schema output. When False, structured() skips straight to prompted JSON
    # + repair rather than attempting (and failing) a native schema call.
    llm_supports_json_schema: bool = True

    llm_model_default: str = "claude-opus-5"
    llm_model_overrides: dict[LLMTask, str] = Field(default_factory=dict)
    llm_effort_default: Literal["low", "medium", "high", "xhigh", "max"] = "high"
    # Coding is the documented xhigh case; game code is the hardest thing we generate.
    llm_effort_overrides: dict[LLMTask, str] = Field(
        default_factory=lambda: {LLMTask.game_code: "xhigh"}
    )
    # Thinking is on by default on current models and max_tokens caps thinking +
    # response text together, so these are sized well above the old 8192.
    llm_max_tokens_default: int = 8_000
    llm_max_tokens_overrides: dict[LLMTask, int] = Field(
        default_factory=lambda: {
            LLMTask.narrative: 16_000,
            LLMTask.game_code: 16_000,
            LLMTask.chat: 8_000,
            LLMTask.profile_description: 1_000,
        }
    )

    # --- auth ---------------------------------------------------------------
    google_client_id: str = ""
    session_secret: SecretStr = SecretStr("")
    access_token_ttl_seconds: int = 900  # 15 min
    refresh_token_ttl_seconds: int = 2_592_000  # 30 days
    # Mounts a dev-login route so the whole stack runs with no cloud accounts.
    # The production validator below refuses to start if this is left on.
    dev_auth_bypass: bool = False

    # --- http ---------------------------------------------------------------
    cors_origins: list[AnyHttpUrl] = Field(default_factory=list)

    # --- inference models (worker) ------------------------------------------
    whisper_model: str = "distil-large-v3"
    whisper_compute_type: str = "int8"
    piper_voice_dir: Path = Path("/data/models/piper")
    # Language -> Piper voice model filename (relative to piper_voice_dir;
    # PiperVoice.load reads the matching "<file>.json" config alongside it).
    # The exact four languages the old Polly integration covered
    # (Joanna/Conchita/Celine/Marlene) — see server/main.py's voice_map.
    piper_voice_map: dict[str, str] = Field(
        default_factory=lambda: {
            "en-US": "en_US-lessac-medium.onnx",
            "es-ES": "es_ES-davefx-medium.onnx",
            "fr-FR": "fr_FR-siwis-medium.onnx",
            "de-DE": "de_DE-thorsten-medium.onnx",
        }
    )
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    # --- retrieval ----------------------------------------------------------
    chunk_tokens: int = 512
    chunk_overlap_tokens: int = 64
    qdrant_collection: str = "chunks"

    @model_validator(mode="after")
    def _production_guards(self) -> Settings:
        """Fail fast rather than start a misconfigured production process."""
        if self.environment is not Environment.production:
            return self

        problems: list[str] = []
        if self.dev_auth_bypass:
            problems.append("dev_auth_bypass must be off in production")
        if not self.cors_origins:
            problems.append("cors_origins must be set in production")
        if len(self.session_secret.get_secret_value()) < 32:
            problems.append("session_secret must be at least 32 characters")
        if not self.anthropic_api_key.get_secret_value():
            problems.append("anthropic_api_key is required (ingestion always uses Anthropic)")
        if self.llm_backend != "anthropic" and not self.llm_base_url:
            problems.append("llm_base_url is required when llm_backend is not 'anthropic'")
        if not self.google_client_id:
            problems.append("google_client_id is required")
        if self.storage_backend == "minio" and not self.minio_endpoint:
            problems.append("minio_endpoint is required when storage_backend=minio")

        if problems:
            raise ValueError("invalid production configuration: " + "; ".join(problems))
        return self

    def generation_api_key(self) -> str:
        """API key for the generation backend — the dedicated key if set,
        otherwise the Anthropic key (valid when llm_backend == "anthropic")."""
        if self.llm_api_key is not None:
            return self.llm_api_key.get_secret_value()
        return self.anthropic_api_key.get_secret_value()

    def model_for(self, task: LLMTask) -> str:
        return self.llm_model_overrides.get(task, self.llm_model_default)

    def effort_for(self, task: LLMTask) -> str:
        return self.llm_effort_overrides.get(task, self.llm_effort_default)

    def max_tokens_for(self, task: LLMTask) -> int:
        return self.llm_max_tokens_overrides.get(task, self.llm_max_tokens_default)


@lru_cache
def get_settings() -> Settings:
    return Settings()
