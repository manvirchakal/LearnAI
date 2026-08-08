from __future__ import annotations

import pytest
from bson import ObjectId

from learnai.errors import NotFound
from learnai.repositories.materials import MaterialRepository
from learnai.schemas.documents import TOCResult, TreeNode
from tests.fakes.mongo import FakeAsyncDatabase


@pytest.fixture
def db() -> FakeAsyncDatabase:
    return FakeAsyncDatabase()


async def test_create_then_get(db: FakeAsyncDatabase) -> None:
    repo = MaterialRepository(db, ObjectId())  # type: ignore[arg-type]

    material_id = await repo.create(
        filename="calculus.pdf", content_type="application/pdf", storage_key="k1", size_bytes=1024
    )

    doc = await repo.get(material_id)
    assert doc["filename"] == "calculus.pdf"
    assert doc["status"] == "uploaded"
    assert doc["page_count"] is None
    assert doc["tree"] is None


async def test_get_of_missing_material_raises_not_found(db: FakeAsyncDatabase) -> None:
    repo = MaterialRepository(db, ObjectId())  # type: ignore[arg-type]
    with pytest.raises(NotFound):
        await repo.get(ObjectId())


async def test_get_of_another_owners_material_raises_not_found(db: FakeAsyncDatabase) -> None:
    owner_a, owner_b = ObjectId(), ObjectId()
    repo_a = MaterialRepository(db, owner_a)  # type: ignore[arg-type]
    repo_b = MaterialRepository(db, owner_b)  # type: ignore[arg-type]

    material_id = await repo_a.create(
        filename="a.pdf", content_type="application/pdf", storage_key="k", size_bytes=1
    )

    with pytest.raises(NotFound):
        await repo_b.get(material_id)


async def test_mark_toc_processing_sets_status_and_page_count(db: FakeAsyncDatabase) -> None:
    repo = MaterialRepository(db, ObjectId())  # type: ignore[arg-type]
    material_id = await repo.create(
        filename="a.pdf", content_type="application/pdf", storage_key="k", size_bytes=1
    )

    await repo.mark_toc_processing(material_id, page_count=42)

    doc = await repo.get(material_id)
    assert doc["status"] == "toc_processing"
    assert doc["page_count"] == 42


async def test_mark_toc_processing_on_missing_material_raises_not_found(
    db: FakeAsyncDatabase,
) -> None:
    repo = MaterialRepository(db, ObjectId())  # type: ignore[arg-type]
    with pytest.raises(NotFound):
        await repo.mark_toc_processing(ObjectId(), page_count=1)


async def test_set_toc_result_stores_tree_and_marks_ready(db: FakeAsyncDatabase) -> None:
    repo = MaterialRepository(db, ObjectId())  # type: ignore[arg-type]
    material_id = await repo.create(
        filename="a.pdf", content_type="application/pdf", storage_key="k", size_bytes=1
    )
    tree = TOCResult(
        tree=[TreeNode(node_id="1", title="Chapter 1", start_page=1, end_page=10)],
        confidence="high",
    )

    await repo.set_toc_result(material_id, tree)

    doc = await repo.get(material_id)
    assert doc["status"] == "toc_ready"
    assert doc["tree"]["tree"][0]["title"] == "Chapter 1"
    assert doc["error"] is None


async def test_mark_toc_failed_records_error(db: FakeAsyncDatabase) -> None:
    repo = MaterialRepository(db, ObjectId())  # type: ignore[arg-type]
    material_id = await repo.create(
        filename="a.pdf", content_type="application/pdf", storage_key="k", size_bytes=1
    )

    await repo.mark_toc_failed(material_id, error="Anthropic declined the request")

    doc = await repo.get(material_id)
    assert doc["status"] == "toc_failed"
    assert doc["error"] == "Anthropic declined the request"


async def test_list_all_is_owner_scoped(db: FakeAsyncDatabase) -> None:
    owner_a, owner_b = ObjectId(), ObjectId()
    repo_a = MaterialRepository(db, owner_a)  # type: ignore[arg-type]
    repo_b = MaterialRepository(db, owner_b)  # type: ignore[arg-type]

    await repo_a.create(
        filename="a1.pdf", content_type="application/pdf", storage_key="k1", size_bytes=1
    )
    await repo_a.create(
        filename="a2.pdf", content_type="application/pdf", storage_key="k2", size_bytes=1
    )
    await repo_b.create(
        filename="b1.pdf", content_type="application/pdf", storage_key="k3", size_bytes=1
    )

    assert {d["filename"] for d in await repo_a.list_all()} == {"a1.pdf", "a2.pdf"}
    assert {d["filename"] for d in await repo_b.list_all()} == {"b1.pdf"}
