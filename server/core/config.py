from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List


class Settings(BaseSettings):
    # AWS Bedrock — only remaining AWS dependency (Claude LLM)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_DEFAULT_REGION: str = "us-east-1"
    BEDROCK_MODEL_HAIKU: str = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    BEDROCK_MODEL_SONNET: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

    # Local storage root
    DATA_DIR: Path = Path(__file__).parent.parent / "data"

    # ChromaDB persistent directory
    CHROMA_DIR: Path = Path(__file__).parent.parent / "data" / "vectorstore"

    # Sentence-transformers model for local embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # faster-whisper model size: tiny | base | small | medium | large-v3
    WHISPER_MODEL: str = "base"

    # argostranslate: source language assumed English
    TRANSLATE_SOURCE_LANG: str = "en"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()

# Ensure local data directories exist at import time
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
