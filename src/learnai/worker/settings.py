"""ARQ worker configuration.

Empty task list for now — real tasks (``transcribe_material``, ``ocr_material``,
``generate_bundle``, ``index_material``, ...) land in Phases 3-4 as the
services they call are built. This exists in Phase 0 so the worker container
has something valid to run, proving the image and the Redis connection work
before there's any actual work to do.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from arq.connections import RedisSettings

from learnai.config import get_settings
from learnai.logging import configure_logging, get_logger

logger = get_logger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    configure_logging(settings)
    get_logger(__name__).info("worker_startup")


async def shutdown(ctx: dict[str, Any]) -> None:
    get_logger(__name__).info("worker_shutdown")


class WorkerSettings:
    functions: list[Callable[..., Any]] = []  # noqa: RUF012 — populated starting Phase 3
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
