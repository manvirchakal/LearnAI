from __future__ import annotations

import pytest
from bson import ObjectId

from learnai.repositories.sections import SectionRepository
from learnai.schemas.documents import Citation, SectionContent
from tests.fakes.mongo import FakeAsyncDatabase


@pytest.fixture
def db() -> FakeAsyncDatabase:
    return FakeAsyncDatabase()


async def test_get_returns_none_before_extraction(db: FakeAsyncDatabase) -> None:
    repo = SectionRepository(db, ObjectId())  # type: ignore[arg-type]
    assert await repo.get(ObjectId(), "1.1") is None


async def test_upsert_then_get_roundtrips(db: FakeAsyncDatabase) -> None:
    repo = SectionRepository(db, ObjectId())  # type: ignore[arg-type]
    material_id = ObjectId()
    section = SectionContent(
        node_id="1.1",
        text="The limit of a function...",
        citations=[Citation(cited_text="The limit of a function", start_page=3, end_page=3)],
    )

    await repo.upsert(material_id, section)

    doc = await repo.get(material_id, "1.1")
    assert doc is not None
    assert doc["text"] == "The limit of a function..."
    assert doc["citations"][0]["start_page"] == 3
    assert doc["created_at"] is not None


async def test_upsert_overwrites_content_but_keeps_original_created_at(
    db: FakeAsyncDatabase,
) -> None:
    repo = SectionRepository(db, ObjectId())  # type: ignore[arg-type]
    material_id = ObjectId()

    await repo.upsert(material_id, SectionContent(node_id="1.1", text="first"))
    first = await repo.get(material_id, "1.1")
    assert first is not None

    await repo.upsert(material_id, SectionContent(node_id="1.1", text="second"))
    second = await repo.get(material_id, "1.1")

    assert second is not None
    assert second["text"] == "second"
    assert second["created_at"] == first["created_at"]


async def test_sections_are_scoped_by_owner(db: FakeAsyncDatabase) -> None:
    owner_a, owner_b = ObjectId(), ObjectId()
    repo_a = SectionRepository(db, owner_a)  # type: ignore[arg-type]
    repo_b = SectionRepository(db, owner_b)  # type: ignore[arg-type]
    material_id = ObjectId()

    await repo_a.upsert(material_id, SectionContent(node_id="1.1", text="owner a's text"))

    assert await repo_b.get(material_id, "1.1") is None
    doc = await repo_a.get(material_id, "1.1")
    assert doc is not None
    assert doc["text"] == "owner a's text"


async def test_sections_are_scoped_by_material(db: FakeAsyncDatabase) -> None:
    repo = SectionRepository(db, ObjectId())  # type: ignore[arg-type]
    material_a, material_b = ObjectId(), ObjectId()

    await repo.upsert(material_a, SectionContent(node_id="1.1", text="from material a"))

    assert await repo.get(material_b, "1.1") is None
