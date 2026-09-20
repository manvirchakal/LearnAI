"""The worker process's own wiring.

``main.py``'s ``lifespan`` gets exercised by every e2e suite (they run the
real app through ``TestClient``); the worker's equivalent has no such
coverage — it only runs inside a real ARQ process. Its failure mode is
quiet and production-only: a task reads a ``ctx`` key that ``startup``
never set, or a newly written task is never registered, and nothing
notices until a job is actually enqueued. These tests are what notice.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from learnai.worker.settings import WorkerSettings, shutdown, startup
from learnai.worker.tasks import extract_toc_task, import_youtube_task, transcribe_lecture_task

# The union of every ctx key worker/tasks.py reads. A task pulling a
# dependency this list doesn't mention means startup isn't building it.
_REQUIRED_CTX_KEYS = {
    "settings",
    "db",
    "storage",
    "extractor",
    "asr",
    "embedder",
    "vector_store",
}


@pytest.fixture
async def started_ctx() -> Any:
    ctx: dict[str, Any] = {}
    # The one call in startup that actually talks to a dependency;
    # everything else it builds is lazy by construction.
    with patch("learnai.worker.settings.ensure_collection", new=AsyncMock()):
        await startup(ctx)
    yield ctx
    await shutdown(ctx)


async def test_startup_builds_every_dependency_the_tasks_read(started_ctx: dict[str, Any]) -> None:
    assert set(started_ctx) >= _REQUIRED_CTX_KEYS


async def test_startup_survives_an_unreachable_qdrant() -> None:
    """Bootstrapping the vector collection is best-effort: a Qdrant that
    isn't up yet must not stop the worker from starting and draining jobs
    that don't touch it."""
    ctx: dict[str, Any] = {}
    with patch(
        "learnai.worker.settings.ensure_collection",
        new=AsyncMock(side_effect=ConnectionError("qdrant is down")),
    ):
        await startup(ctx)

    assert set(ctx) >= _REQUIRED_CTX_KEYS
    await shutdown(ctx)


def test_every_task_is_registered_with_the_worker() -> None:
    """An unregistered task is a silent failure — the router enqueues it
    happily and the worker never picks it up."""
    assert set(WorkerSettings.functions) == {
        extract_toc_task,
        transcribe_lecture_task,
        import_youtube_task,
    }
