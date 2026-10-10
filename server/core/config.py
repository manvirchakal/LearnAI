from pathlib import Path
from typing import List, Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── LLM ───────────────────────────────────────────────────────────────────
    # "openai": any OpenAI-compatible server (vLLM, llama.cpp, Ollama, LiteLLM)
    # "bedrock": Claude via AWS Bedrock
    LLM_PROVIDER: Literal["openai", "bedrock"] = "openai"
    # Model roles. LLM_MODEL writes narratives, games and chat replies;
    # LLM_VISION_MODEL reads scanned tables of contents. Empty = provider default.
    LLM_MODEL: str = ""
    LLM_VISION_MODEL: str = ""
    # Turn off when the served model can't take images: scanned-TOC parsing is
    # then skipped and books without a PDF outline become a single section.
    LLM_VISION_ENABLED: bool = True
    # The served model's context length in tokens (vLLM --max-model-len). The
    # budgets below are derived from it, so this is the one number to change
    # when the model server changes.
    LLM_CONTEXT_TOKENS: int = 131_072
    # Upper bound on generated tokens per call. Unset = a quarter of the context.
    LLM_MAX_OUTPUT_TOKENS: Optional[int] = None
    LLM_TIMEOUT_SECONDS: float = 600
    # Source material (a section, a collection) is truncated to this many
    # characters before prompting. Unset = 40% of the context at ~4 chars/token
    # (~210k chars at 128k tokens).
    LLM_MAX_SOURCE_CHARS: Optional[int] = None

    # OpenAI-compatible endpoint (vLLM serves it at http://<host>:<port>/v1)
    OPENAI_BASE_URL: str = "http://localhost:8001/v1"
    OPENAI_API_KEY: str = "EMPTY"

    # AWS Bedrock. Leave the keys empty to use boto3's default credential chain.
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_DEFAULT_REGION: str = "us-east-1"

    # ── Embeddings (RAG) ──────────────────────────────────────────────────────
    # "openai": POST {EMBEDDING_BASE_URL}/embeddings (e.g. vLLM --task embed)
    # "local": sentence-transformers in-process (pip install ".[local-ml]")
    EMBEDDING_PROVIDER: Literal["openai", "local"] = "openai"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_BASE_URL: str = ""  # empty = OPENAI_BASE_URL
    EMBEDDING_BATCH_SIZE: int = 64

    # ── Speech-to-text ────────────────────────────────────────────────────────
    # "openai": POST {STT_BASE_URL}/audio/transcriptions (e.g. vLLM serving Whisper)
    # "local": faster-whisper in-process (pip install ".[local-ml]")
    STT_PROVIDER: Literal["openai", "local"] = "openai"
    STT_MODEL: str = "openai/whisper-large-v3-turbo"  # for "local": tiny | base | small | medium | large-v3
    STT_BASE_URL: str = ""  # empty = OPENAI_BASE_URL
    # Remote audio is re-encoded with ffmpeg into chunks of this length (keeps
    # each upload under the server's file-size limit)
    STT_CHUNK_SECONDS: int = 600

    # ── Translation ───────────────────────────────────────────────────────────
    # "llm": translate with the chat model; "argos": argostranslate in-process
    TRANSLATION_PROVIDER: Literal["llm", "argos"] = "llm"

    # ── Storage ───────────────────────────────────────────────────────────────
    DATA_DIR: Path = Path(__file__).parent.parent / "data"
    CHROMA_DIR: Path = Path(__file__).parent.parent / "data" / "vectorstore"
    MAX_UPLOAD_MB: int = 200

    # ── Server ────────────────────────────────────────────────────────────────
    # Only needed if browsers call the API directly instead of through Next.js
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Derived ───────────────────────────────────────────────────────────────
    @property
    def max_output_tokens(self) -> int:
        return self.LLM_MAX_OUTPUT_TOKENS or self.LLM_CONTEXT_TOKENS // 4

    @property
    def max_source_chars(self) -> int:
        return self.LLM_MAX_SOURCE_CHARS or self.context_chars(0.4)

    def context_chars(self, fraction: float) -> int:
        """A fraction of the context window, in characters (~4 per token)."""
        return int(self.LLM_CONTEXT_TOKENS * fraction * 4)

    @property
    def embedding_base_url(self) -> str:
        return self.EMBEDDING_BASE_URL or self.OPENAI_BASE_URL

    @property
    def stt_base_url(self) -> str:
        return self.STT_BASE_URL or self.OPENAI_BASE_URL


settings = Settings()

# Ensure local data directories exist at import time
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
