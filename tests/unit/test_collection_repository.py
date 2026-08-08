from __future__ import annotations

import pytest
from bson import ObjectId

from learnai.errors import NotFound
from learnai.repositories.collections import CollectionRepository
from tests.fakes.mongo import FakeAsyncDatabase


@pytest.fixture
def db() -> FakeAsyncDatabase:
    return FakeAsyncDatabase()


async def test_create_then_get(db: FakeAsyncDatabase) -> None:
    repo = CollectionRepository(db, ObjectId())  # type: ignore[arg-type]

    collection_id = await repo.create(name="Calculus", kind="manual")

    doc = await repo.get(collection_id)
    assert doc["name"] == "Calculus"
    assert doc["kind"] == "manual"
    assert doc["material_refs"] == []
    assert doc["parent_collection_id"] is None


async def test_get_of_missing_collection_raises_not_found(db: FakeAsyncDatabase) -> None:
    repo = CollectionRepository(db, ObjectId())  # type: ignore[arg-type]
    with pytest.raises(NotFound):
        await repo.get(ObjectId())


async def test_get_of_another_owners_collection_also_raises_not_found(
    db: FakeAsyncDatabase,
) -> None:
    """Not a 403 — a 404. Same shape whether the document doesn't exist or
    belongs to someone else; no existence oracle."""
    owner_a, owner_b = ObjectId(), ObjectId()
    repo_a = CollectionRepository(db, owner_a)  # type: ignore[arg-type]
    repo_b = CollectionRepository(db, owner_b)  # type: ignore[arg-type]

    collection_id = await repo_a.create(name="A's notes", kind="manual")

    with pytest.raises(NotFound):
        await repo_b.get(collection_id)


async def test_list_all_returns_newest_first(db: FakeAsyncDatabase) -> None:
    repo = CollectionRepository(db, ObjectId())  # type: ignore[arg-type]

    id1 = await repo.create(name="first", kind="manual")
    id2 = await repo.create(name="second", kind="manual")
    id3 = await repo.create(name="third", kind="manual")

    # The fake doesn't implement real sort, so this only checks membership +
    # scoping here; ordering itself is verified against real Mongo in
    # tests/integration (the {owner_id, created_at} index this relies on).
    ids = {doc["_id"] for doc in await repo.list_all()}
    assert ids == {id1, id2, id3}


async def test_list_all_is_owner_scoped(db: FakeAsyncDatabase) -> None:
    owner_a, owner_b = ObjectId(), ObjectId()
    repo_a = CollectionRepository(db, owner_a)  # type: ignore[arg-type]
    repo_b = CollectionRepository(db, owner_b)  # type: ignore[arg-type]

    await repo_a.create(name="a1", kind="manual")
    await repo_a.create(name="a2", kind="manual")
    await repo_b.create(name="b1", kind="manual")

    assert {d["name"] for d in await repo_a.list_all()} == {"a1", "a2"}
    assert {d["name"] for d in await repo_b.list_all()} == {"b1"}


async def test_update_materials_replaces_refs(db: FakeAsyncDatabase) -> None:
    repo = CollectionRepository(db, ObjectId())  # type: ignore[arg-type]
    collection_id = await repo.create(name="Calculus", kind="manual")

    refs = [{"material_id": ObjectId(), "section_ids": [], "added_at": None}]
    await repo.update_materials(collection_id, refs)

    doc = await repo.get(collection_id)
    assert doc["material_refs"] == refs


async def test_update_materials_on_missing_collection_raises_not_found(
    db: FakeAsyncDatabase,
) -> None:
    repo = CollectionRepository(db, ObjectId())  # type: ignore[arg-type]
    with pytest.raises(NotFound):
        await repo.update_materials(ObjectId(), [])


async def test_parent_child_relationship_is_queryable(db: FakeAsyncDatabase) -> None:
    """The fix for the old orphaned-ID bug: a section collection carries a
    real parent_collection_id pointing at a chapter that actually exists,
    settable at creation and queryable directly — no separately-generated,
    unlinked IDs."""
    repo = CollectionRepository(db, ObjectId())  # type: ignore[arg-type]

    chapter_id = await repo.create(name="Chapter 1", kind="chapter")
    section_1_id = await repo.create(
        name="1.1 Limits", kind="section", parent_collection_id=chapter_id
    )
    section_2_id = await repo.create(
        name="1.2 Continuity", kind="section", parent_collection_id=chapter_id
    )
    await repo.create(name="Chapter 2", kind="chapter")  # unrelated sibling

    children = await repo.list_children(chapter_id)
    child_ids = {doc["_id"] for doc in children}

    assert child_ids == {section_1_id, section_2_id}
    for child in children:
        assert child["parent_collection_id"] == chapter_id
        # And the parent itself is a real, fetchable document — not a dangling ID.
        parent = await repo.get(child["parent_collection_id"])
        assert parent["name"] == "Chapter 1"
