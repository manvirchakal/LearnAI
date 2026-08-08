"""ScopedRepository: the tenant-isolation invariant, tested at the unit
level against a fake collection. See tests/integration for the same
guarantees re-verified against real MongoDB.
"""

from __future__ import annotations

from typing import Any

import pytest
from bson import ObjectId

from learnai.repositories.base import ScopedRepository, ScopeViolation
from tests.fakes.mongo import FakeAsyncDatabase


class _WidgetRepo(ScopedRepository[dict[str, Any]]):
    COLLECTION = "widgets"


@pytest.fixture
def db() -> FakeAsyncDatabase:
    return FakeAsyncDatabase()


async def test_insert_injects_owner_id(db: FakeAsyncDatabase) -> None:
    owner = ObjectId()
    repo = _WidgetRepo(db, owner)  # type: ignore[arg-type]

    widget_id = await repo.insert_one({"name": "gizmo"})

    stored = db["widgets"]._docs[str(widget_id)]
    assert stored["owner_id"] == owner
    assert stored["name"] == "gizmo"


async def test_insert_rejects_explicit_owner_id(db: FakeAsyncDatabase) -> None:
    repo = _WidgetRepo(db, ObjectId())  # type: ignore[arg-type]
    with pytest.raises(ScopeViolation):
        await repo.insert_one({"name": "gizmo", "owner_id": ObjectId()})


async def test_find_one_never_returns_another_owners_document(db: FakeAsyncDatabase) -> None:
    owner_a, owner_b = ObjectId(), ObjectId()
    repo_a = _WidgetRepo(db, owner_a)  # type: ignore[arg-type]
    repo_b = _WidgetRepo(db, owner_b)  # type: ignore[arg-type]

    widget_id = await repo_a.insert_one({"name": "a-owned"})

    # B looking up A's exact document by _id gets nothing — not a 403, a
    # plain miss. Same as if it never existed.
    assert await repo_b.find_one({"_id": widget_id}) is None
    assert await repo_a.find_one({"_id": widget_id}) is not None


async def test_find_only_returns_the_calling_owners_documents(db: FakeAsyncDatabase) -> None:
    owner_a, owner_b = ObjectId(), ObjectId()
    repo_a = _WidgetRepo(db, owner_a)  # type: ignore[arg-type]
    repo_b = _WidgetRepo(db, owner_b)  # type: ignore[arg-type]

    await repo_a.insert_one({"name": "a1"})
    await repo_a.insert_one({"name": "a2"})
    await repo_b.insert_one({"name": "b1"})

    a_names = {doc["name"] async for doc in repo_a.find({})}
    b_names = {doc["name"] async for doc in repo_b.find({})}

    assert a_names == {"a1", "a2"}
    assert b_names == {"b1"}


async def test_update_one_cannot_touch_another_owners_document(db: FakeAsyncDatabase) -> None:
    owner_a, owner_b = ObjectId(), ObjectId()
    repo_a = _WidgetRepo(db, owner_a)  # type: ignore[arg-type]
    repo_b = _WidgetRepo(db, owner_b)  # type: ignore[arg-type]

    widget_id = await repo_a.insert_one({"name": "original"})

    result = await repo_b.update_one({"_id": widget_id}, {"$set": {"name": "hijacked"}})
    assert result.matched_count == 0

    still_original = await repo_a.find_one({"_id": widget_id})
    assert still_original is not None
    assert still_original["name"] == "original"


async def test_update_one_upsert_creates_a_correctly_owned_document(
    db: FakeAsyncDatabase,
) -> None:
    owner = ObjectId()
    repo = _WidgetRepo(db, owner)  # type: ignore[arg-type]

    await repo.update_one({}, {"$set": {"name": "created-via-upsert"}}, upsert=True)

    doc = await repo.find_one({})
    assert doc is not None
    assert doc["owner_id"] == owner
    assert doc["name"] == "created-via-upsert"


async def test_update_one_upsert_does_not_duplicate_on_second_call(
    db: FakeAsyncDatabase,
) -> None:
    owner = ObjectId()
    repo = _WidgetRepo(db, owner)  # type: ignore[arg-type]

    await repo.update_one({}, {"$set": {"name": "v1"}}, upsert=True)
    await repo.update_one({}, {"$set": {"name": "v2"}}, upsert=True)

    assert await repo.count({}) == 1
    doc = await repo.find_one({})
    assert doc is not None
    assert doc["name"] == "v2"


async def test_delete_one_cannot_touch_another_owners_document(db: FakeAsyncDatabase) -> None:
    owner_a, owner_b = ObjectId(), ObjectId()
    repo_a = _WidgetRepo(db, owner_a)  # type: ignore[arg-type]
    repo_b = _WidgetRepo(db, owner_b)  # type: ignore[arg-type]

    widget_id = await repo_a.insert_one({"name": "safe"})

    result = await repo_b.delete_one({"_id": widget_id})
    assert result.deleted_count == 0
    assert await repo_a.find_one({"_id": widget_id}) is not None


async def test_count_is_scoped_per_owner(db: FakeAsyncDatabase) -> None:
    owner_a, owner_b = ObjectId(), ObjectId()
    repo_a = _WidgetRepo(db, owner_a)  # type: ignore[arg-type]
    repo_b = _WidgetRepo(db, owner_b)  # type: ignore[arg-type]

    await repo_a.insert_one({"name": "a1"})
    await repo_a.insert_one({"name": "a2"})
    await repo_b.insert_one({"name": "b1"})

    assert await repo_a.count({}) == 2
    assert await repo_b.count({}) == 1


@pytest.mark.parametrize(
    "method_call",
    [
        lambda repo: repo.find_one({"owner_id": ObjectId()}),
        lambda repo: repo.update_one({"owner_id": ObjectId()}, {"$set": {}}),
        lambda repo: repo.delete_one({"owner_id": ObjectId()}),
        lambda repo: repo.count({"owner_id": ObjectId()}),
    ],
)
async def test_passing_owner_id_explicitly_in_a_query_always_raises(
    db: FakeAsyncDatabase, method_call: object
) -> None:
    repo = _WidgetRepo(db, ObjectId())  # type: ignore[arg-type]
    with pytest.raises(ScopeViolation):
        await method_call(repo)  # type: ignore[operator]


def test_find_also_raises_synchronously_on_owner_id_in_query(db: FakeAsyncDatabase) -> None:
    # find() is not async (it returns a cursor to iterate), so its
    # ScopeViolation surfaces immediately on the call, not on first iteration.
    repo = _WidgetRepo(db, ObjectId())  # type: ignore[arg-type]
    with pytest.raises(ScopeViolation):
        repo.find({"owner_id": ObjectId()})
