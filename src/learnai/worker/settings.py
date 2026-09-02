"""ARQ worker configuration.

Builds the worker process's own singletons on startup — mirroring what
``main.py``'s ``lifespan`` does for the API process. The two processes never
share ``app.state``; Redis (the job queue) is the only thing they have in
common.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import anthropic
from arq.connections import RedisSettings
from qdrant_client import AsyncQdrantClient

from learnai.config import get_settings
from learnai.db.mongo import create_mongo_client, get_database
from learnai.logging import configure_logging, get_logger
from learnai.services.asr import ASREngine, FasterWhisperASR
from learnai.services.extraction.anthropic_pdf import AnthropicPDFExtractor
from learnai.services.retrieval.embedder import Embedder, FastEmbedEmbedder
from learnai.services.retrieval.vector_store import (
    QdrantVectorStore,
    VectorStore,
    ensure_collection,
)
from learnai.services.storage.base import StorageBackend
from learnai.services.storage.local import LocalFilesystemStorage
from learnai.worker.tasks import extract_toc_task, import_youtube_task, transcribe_lecture_task

logger = get_logger(__name__)


def _build_storage(settings: Any) -> StorageBackend:
    if settings.storage_backend == "local":
        return LocalFilesystemStorage(settings.storage_root)
    raise NotImplementedError(
        f"storage_backend={settings.storage_backend!r} is not implemented yet"
    )


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    configure_logging(settings)
    ctx["settings"] = settings

    mongo_client = create_mongo_client(settings)
    ctx["mongo_client"] = mongo_client
    ctx["db"] = get_database(mongo_client, settings)
    ctx["storage"] = _build_storage(settings)

    anthropic_client = anthropic.AsyncAnthropic(
        api_key=settings.anthropic_api_key.get_secret_value()
    )
    ctx["anthropic_client"] = anthropic_client
    ctx["extractor"] = AnthropicPDFExtractor(anthropic_client, settings)

    # Same reasoning as main.py's lifespan: fail fast rather than hang on a
    # down dependency, and defer the actual collection-existence check to
    # ensure_collection rather than the client constructor itself.
    ctx["qdrant_client"] = AsyncQdrantClient(url=settings.qdrant_url, timeout=5)
    try:
        await ensure_collection(
            ctx["qdrant_client"],
            name=settings.qdrant_collection,
            vector_size=settings.embedding_dim,
        )
    except Exception:
        logger.error("qdrant_collection_bootstrap_failed", exc_info=True)
    vector_store: VectorStore = QdrantVectorStore(
        ctx["qdrant_client"], collection_name=settings.qdrant_collection
    )
    ctx["vector_store"] = vector_store

    # Model load deferred to first use (see FastEmbedEmbedder/
    # FasterWhisperASR's own docstrings) — constructing these here can
    # never fail worker startup itself.
    embedder: Embedder = FastEmbedEmbedder(settings.embedding_model)
    ctx["embedder"] = embedder
    asr: ASREngine = FasterWhisperASR(settings.whisper_model, settings.whisper_compute_type)
    ctx["asr"] = asr

    get_logger(__name__).info("worker_startup")


async def shutdown(ctx: dict[str, Any]) -> None:
    await ctx["mongo_client"].close()
    await ctx["anthropic_client"].close()
    await ctx["qdrant_client"].close()
    get_logger(__name__).info("worker_shutdown")


class WorkerSettings:
    functions: list[Callable[..., Any]] = [  # noqa: RUF012
        extract_toc_task,
        transcribe_lecture_task,
        import_youtube_task,
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
