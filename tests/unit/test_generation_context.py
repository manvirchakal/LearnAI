"""``collection_content`` against fakes — gathering a collection's
material text for generation, including the lazy-extraction path it
shares with the reader (see ``tests/unit/test_ingestion_pipeline.py``).
"""

from __future__ import annotations

import pymupdf
import pytest
from bson import ObjectId

from learnai.config import Settings
from learnai.errors import ValidationError
from learnai.repositories.materials import MaterialRepository
from learnai.repositories.sections import SectionRepository
from learnai.schemas.documents import SectionContent, TOCResult, TreeNode
from learnai.services.generation.context import collection_content
from tests.fakes.embedder import FakeEmbedder
from tests.fakes.extraction import FakeExtractor
from tests.fakes.mongo import FakeAsyncDatabase
from tests.fakes.storage import FakeStorage
from tests.fakes.vector_store import FakeVectorStore


def _make_pdf(num_pages: int) -> bytes:
    doc = pymupdf.open()  # type: ignore[no-untyped-call]
    for _ in range(num_pages):
        doc.new_page()
    buffer: bytes = doc.tobytes()  # type: ignore[no-untyped-call]
    doc.close()  # type: ignore[no-untyped-call]
    return buffer


@pytest.fixture
def db() -> FakeAsyncDatabase:
    return FakeAsyncDatabase()


@pytest.fixture
def settings() -> Settings:
    return Settings()


async def _seed_ready_material(
    db: FakeAsyncDatabase, owner: ObjectId, *, filename: str = "calculus.pdf"
) -> ObjectId:
    materials = MaterialRepository(db, owner)  # type: ignore[arg-type]
    material_id = await materials.create(
        filename=filename, content_type="application/pdf", storage_key="k", size_bytes=1
    )
    tree = TOCResult(
        tree=[
            TreeNode(node_id="1", title="Chapter 1", start_page=1, end_page=5),
            TreeNode(node_id="2", title="Chapter 2", start_page=6, end_page=10),
        ],
        confidence="high",
    )
    await materials.set_toc_result(material_id, tree)
    return material_id


def _deps(db: FakeAsyncDatabase, owner: ObjectId, settings: Settings) -> dict[str, object]:
    storage = FakeStorage()
    return {
        "materials": MaterialRepository(db, owner),  # type: ignore[arg-type]
        "sections": SectionRepository(db, owner),  # type: ignore[arg-type]
        "storage": storage,
        "extractor": FakeExtractor(),
        "embedder": FakeEmbedder(),
        "vector_store": FakeVectorStore(),
        "settings": settings,
        "owner_id": owner,
    }


async def test_explicit_section_ids_are_extracted_and_joined(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    material_id = await _seed_ready_material(db, owner)
    deps = _deps(db, owner, settings)
    storage: FakeStorage = deps["storage"]  # type: ignore[assignment]
    await storage.put("k", _make_pdf(10), "application/pdf")
    extractor: FakeExtractor = deps["extractor"]  # type: ignore[assignment]
    extractor.section_results["1"] = SectionContent(node_id="1", text="limits content")

    collection = {"material_refs": [{"material_id": material_id, "section_ids": ["1"]}]}
    content = await collection_content(collection, **deps)  # type: ignore[arg-type]

    assert "calculus.pdf" in content
    assert "Chapter 1" in content
    assert "limits content" in content
    assert "Chapter 2" not in content


async def test_empty_section_ids_means_whole_material(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    material_id = await _seed_ready_material(db, owner)
    deps = _deps(db, owner, settings)
    storage: FakeStorage = deps["storage"]  # type: ignore[assignment]
    await storage.put("k", _make_pdf(10), "application/pdf")
    extractor: FakeExtractor = deps["extractor"]  # type: ignore[assignment]
    extractor.section_results["1"] = SectionContent(node_id="1", text="limits content")
    extractor.section_results["2"] = SectionContent(node_id="2", text="derivatives content")

    collection = {"material_refs": [{"material_id": material_id, "section_ids": []}]}
    content = await collection_content(collection, **deps)  # type: ignore[arg-type]

    assert "limits content" in content
    assert "derivatives content" in content


async def test_material_not_toc_ready_is_skipped(db: FakeAsyncDatabase, settings: Settings) -> None:
    owner = ObjectId()
    materials = MaterialRepository(db, owner)  # type: ignore[arg-type]
    not_ready_id = await materials.create(
        filename="a.pdf", content_type="application/pdf", storage_key="k", size_bytes=1
    )
    ready_id = await _seed_ready_material(db, owner, filename="b.pdf")
    deps = _deps(db, owner, settings)
    storage: FakeStorage = deps["storage"]  # type: ignore[assignment]
    await storage.put("k", _make_pdf(10), "application/pdf")
    extractor: FakeExtractor = deps["extractor"]  # type: ignore[assignment]
    extractor.section_results["1"] = SectionContent(node_id="1", text="ready content")

    collection = {
        "material_refs": [
            {"material_id": not_ready_id, "section_ids": []},
            {"material_id": ready_id, "section_ids": ["1"]},
        ]
    }
    content = await collection_content(collection, **deps)  # type: ignore[arg-type]

    assert "ready content" in content
    assert "a.pdf" not in content


async def test_no_ready_content_raises_validation_error(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    deps = _deps(db, owner, settings)

    with pytest.raises(ValidationError):
        await collection_content({"material_refs": []}, **deps)  # type: ignore[arg-type]
