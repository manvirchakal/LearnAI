from __future__ import annotations

import pytest
from bson import ObjectId

from learnai.repositories.artifacts import ArtifactRepository
from tests.fakes.mongo import FakeAsyncDatabase


@pytest.fixture
def db() -> FakeAsyncDatabase:
    return FakeAsyncDatabase()


async def test_get_before_upsert_is_none(db: FakeAsyncDatabase) -> None:
    repo = ArtifactRepository(db, ObjectId())  # type: ignore[arg-type]
    assert await repo.get(ObjectId(), "narrative", "fp1") is None


async def test_upsert_then_get_roundtrips(db: FakeAsyncDatabase) -> None:
    repo = ArtifactRepository(db, ObjectId())  # type: ignore[arg-type]
    collection_id = ObjectId()

    await repo.upsert(collection_id, "narrative", "fp1", {"text": "once upon a time"})

    doc = await repo.get(collection_id, "narrative", "fp1")
    assert doc is not None
    assert doc["content"] == {"text": "once upon a time"}
    assert doc["created_at"] is not None


async def test_different_fingerprint_is_a_cache_miss(db: FakeAsyncDatabase) -> None:
    repo = ArtifactRepository(db, ObjectId())  # type: ignore[arg-type]
    collection_id = ObjectId()

    await repo.upsert(collection_id, "narrative", "fp1", {"text": "a"})

    assert await repo.get(collection_id, "narrative", "fp2") is None


async def test_upsert_overwrites_content_but_keeps_original_created_at(
    db: FakeAsyncDatabase,
) -> None:
    repo = ArtifactRepository(db, ObjectId())  # type: ignore[arg-type]
    collection_id = ObjectId()

    await repo.upsert(collection_id, "narrative", "fp1", {"text": "first"})
    first = await repo.get(collection_id, "narrative", "fp1")
    assert first is not None

    await repo.upsert(collection_id, "narrative", "fp1", {"text": "second"})
    second = await repo.get(collection_id, "narrative", "fp1")

    assert second is not None
    assert second["content"] == {"text": "second"}
    assert second["created_at"] == first["created_at"]


async def test_artifacts_are_owner_scoped(db: FakeAsyncDatabase) -> None:
    owner_a, owner_b = ObjectId(), ObjectId()
    repo_a = ArtifactRepository(db, owner_a)  # type: ignore[arg-type]
    repo_b = ArtifactRepository(db, owner_b)  # type: ignore[arg-type]
    collection_id = ObjectId()

    await repo_a.upsert(collection_id, "narrative", "fp1", {"text": "owner a's narrative"})

    assert await repo_b.get(collection_id, "narrative", "fp1") is None
