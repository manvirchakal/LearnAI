from __future__ import annotations

import pytest
from bson import ObjectId

from learnai.errors import NotFound
from learnai.repositories.jobs import JobRepository
from tests.fakes.mongo import FakeAsyncDatabase


@pytest.fixture
def db() -> FakeAsyncDatabase:
    return FakeAsyncDatabase()


async def test_create_then_get(db: FakeAsyncDatabase) -> None:
    repo = JobRepository(db, ObjectId())  # type: ignore[arg-type]

    job_id = await repo.create(kind="toc_extraction", payload={"material_id": "abc"})

    doc = await repo.get(job_id)
    assert doc["kind"] == "toc_extraction"
    assert doc["payload"] == {"material_id": "abc"}
    assert doc["status"] == "queued"
    assert doc["result"] is None
    assert doc["error"] is None


async def test_get_of_missing_job_raises_not_found(db: FakeAsyncDatabase) -> None:
    repo = JobRepository(db, ObjectId())  # type: ignore[arg-type]
    with pytest.raises(NotFound):
        await repo.get(ObjectId())


async def test_mark_running_then_succeeded(db: FakeAsyncDatabase) -> None:
    repo = JobRepository(db, ObjectId())  # type: ignore[arg-type]
    job_id = await repo.create(kind="toc_extraction", payload={})

    await repo.mark_running(job_id)
    assert (await repo.get(job_id))["status"] == "running"

    await repo.mark_succeeded(job_id, result={"page_count": 42})
    doc = await repo.get(job_id)
    assert doc["status"] == "succeeded"
    assert doc["result"] == {"page_count": 42}


async def test_mark_failed_records_error(db: FakeAsyncDatabase) -> None:
    repo = JobRepository(db, ObjectId())  # type: ignore[arg-type]
    job_id = await repo.create(kind="toc_extraction", payload={})

    await repo.mark_failed(job_id, error="Anthropic declined the request")

    doc = await repo.get(job_id)
    assert doc["status"] == "failed"
    assert doc["error"] == "Anthropic declined the request"


async def test_mark_running_on_missing_job_raises_not_found(db: FakeAsyncDatabase) -> None:
    repo = JobRepository(db, ObjectId())  # type: ignore[arg-type]
    with pytest.raises(NotFound):
        await repo.mark_running(ObjectId())


async def test_jobs_are_owner_scoped(db: FakeAsyncDatabase) -> None:
    owner_a, owner_b = ObjectId(), ObjectId()
    repo_a = JobRepository(db, owner_a)  # type: ignore[arg-type]
    repo_b = JobRepository(db, owner_b)  # type: ignore[arg-type]

    job_id = await repo_a.create(kind="toc_extraction", payload={})

    with pytest.raises(NotFound):
        await repo_b.get(job_id)
