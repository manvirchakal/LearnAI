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

from learnai.config import get_settings
from learnai.db.mongo import create_mongo_client, get_database
from learnai.logging import configure_logging, get_logger
from learnai.services.extraction.anthropic_pdf import AnthropicPDFExtractor
from learnai.services.storage.base import StorageBackend
from learnai.services.storage.local import LocalFilesystemStorage
from learnai.worker.tasks import extract_toc_task

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

    mongo_client = create_mongo_client(settings)
    ctx["mongo_client"] = mongo_client
    ctx["db"] = get_database(mongo_client, settings)
    ctx["storage"] = _build_storage(settings)

    anthropic_client = anthropic.AsyncAnthropic(
        api_key=settings.anthropic_api_key.get_secret_value()
    )
    ctx["anthropic_client"] = anthropic_client
    ctx["extractor"] = AnthropicPDFExtractor(anthropic_client, settings)

    get_logger(__name__).info("worker_startup")


async def shutdown(ctx: dict[str, Any]) -> None:
    await ctx["mongo_client"].close()
    await ctx["anthropic_client"].close()
    get_logger(__name__).info("worker_shutdown")


class WorkerSettings:
    functions: list[Callable[..., Any]] = [extract_toc_task]  # noqa: RUF012
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
