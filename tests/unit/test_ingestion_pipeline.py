"""``get_or_extract_section`` against fakes — the service layer directly,
below the router tested end-to-end in ``tests/e2e/test_materials.py``.
Same repository/storage/extractor fakes the worker-task and e2e tests use,
plus fakes for the embedder and vector store to verify the indexing side
effect a fresh extraction now triggers.
"""

from __future__ import annotations

import pymupdf
import pytest
from bson import ObjectId

from learnai.config import Settings
from learnai.errors import Conflict, NotFound
from learnai.repositories.materials import MaterialRepository
from learnai.repositories.sections import SectionRepository
from learnai.schemas.documents import SectionContent, TOCResult, TreeNode
from learnai.services.ingestion.pipeline import get_or_extract_section
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


async def _seed_ready_material(db: FakeAsyncDatabase, owner: ObjectId) -> ObjectId:
    materials = MaterialRepository(db, owner)  # type: ignore[arg-type]
    material_id = await materials.create(
        filename="calculus.pdf", content_type="application/pdf", storage_key="k", size_bytes=1
    )
    tree = TOCResult(
        tree=[TreeNode(node_id="1", title="Chapter 1", start_page=2, end_page=4)],
        confidence="high",
    )
    await materials.set_toc_result(material_id, tree)
    return material_id


async def test_cache_miss_extracts_slices_and_caches(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    material_id = await _seed_ready_material(db, owner)
    materials = MaterialRepository(db, owner)  # type: ignore[arg-type]
    sections = SectionRepository(db, owner)  # type: ignore[arg-type]
    storage = FakeStorage()
    await storage.put("k", _make_pdf(10), "application/pdf")
    extractor = FakeExtractor()
    extractor.section_results["1"] = SectionContent(node_id="1", text="chapter text", citations=[])

    result = await get_or_extract_section(
        materials=materials,
        sections=sections,
        storage=storage,
        extractor=extractor,
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore(),
        settings=settings,
        owner_id=owner,
        material_id=material_id,
        node_id="1",
    )

    assert result.text == "chapter text"
    assert [c["op"] for c in extractor.calls] == ["upload", "extract_section", "delete"]

    cached = await sections.get(material_id, "1")
    assert cached is not None
    assert cached["text"] == "chapter text"


async def test_cache_miss_indexes_chunks_into_vector_store(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    material_id = await _seed_ready_material(db, owner)
    materials = MaterialRepository(db, owner)  # type: ignore[arg-type]
    sections = SectionRepository(db, owner)  # type: ignore[arg-type]
    storage = FakeStorage()
    await storage.put("k", _make_pdf(10), "application/pdf")
    extractor = FakeExtractor()
    extractor.section_results["1"] = SectionContent(node_id="1", text="chapter text", citations=[])
    vector_store = FakeVectorStore()

    await get_or_extract_section(
        materials=materials,
        sections=sections,
        storage=storage,
        extractor=extractor,
        embedder=FakeEmbedder(),
        vector_store=vector_store,
        settings=settings,
        owner_id=owner,
        material_id=material_id,
        node_id="1",
    )

    assert len(vector_store.points) == 1
    (point,) = vector_store.points.values()
    assert point.owner_id == owner
    assert point.material_id == material_id
    assert point.node_id == "1"
    assert point.node_path == ["1"]
    assert point.text == "chapter text"


async def test_cache_hit_skips_extraction_and_indexing(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    material_id = await _seed_ready_material(db, owner)
    materials = MaterialRepository(db, owner)  # type: ignore[arg-type]
    sections = SectionRepository(db, owner)  # type: ignore[arg-type]
    await sections.upsert(material_id, SectionContent(node_id="1", text="already cached"))
    extractor = FakeExtractor()
    embedder = FakeEmbedder()
    vector_store = FakeVectorStore()

    result = await get_or_extract_section(
        materials=materials,
        sections=sections,
        storage=FakeStorage(),
        extractor=extractor,
        embedder=embedder,
        vector_store=vector_store,
        settings=settings,
        owner_id=owner,
        material_id=material_id,
        node_id="1",
    )

    assert result.text == "already cached"
    assert extractor.calls == []
    assert embedder.calls == []
    assert vector_store.points == {}


async def test_indexing_failure_does_not_break_the_read_path(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    material_id = await _seed_ready_material(db, owner)
    materials = MaterialRepository(db, owner)  # type: ignore[arg-type]
    sections = SectionRepository(db, owner)  # type: ignore[arg-type]
    storage = FakeStorage()
    await storage.put("k", _make_pdf(10), "application/pdf")
    extractor = FakeExtractor()
    extractor.section_results["1"] = SectionContent(node_id="1", text="chapter text", citations=[])

    class _BrokenEmbedder:
        async def embed(self, texts: list[str]) -> list[list[float]]:
            raise RuntimeError("qdrant is down")

    result = await get_or_extract_section(
        materials=materials,
        sections=sections,
        storage=storage,
        extractor=extractor,
        embedder=_BrokenEmbedder(),
        vector_store=FakeVectorStore(),
        settings=settings,
        owner_id=owner,
        material_id=material_id,
        node_id="1",
    )

    assert result.text == "chapter text"
    cached = await sections.get(material_id, "1")
    assert cached is not None


async def test_material_not_ready_raises_conflict(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    materials = MaterialRepository(db, owner)  # type: ignore[arg-type]
    material_id = await materials.create(
        filename="a.pdf", content_type="application/pdf", storage_key="k", size_bytes=1
    )
    sections = SectionRepository(db, owner)  # type: ignore[arg-type]

    with pytest.raises(Conflict):
        await get_or_extract_section(
            materials=materials,
            sections=sections,
            storage=FakeStorage(),
            extractor=FakeExtractor(),
            embedder=FakeEmbedder(),
            vector_store=FakeVectorStore(),
            settings=settings,
            owner_id=owner,
            material_id=material_id,
            node_id="1",
        )


async def test_unknown_node_id_raises_not_found(db: FakeAsyncDatabase, settings: Settings) -> None:
    owner = ObjectId()
    material_id = await _seed_ready_material(db, owner)
    materials = MaterialRepository(db, owner)  # type: ignore[arg-type]
    sections = SectionRepository(db, owner)  # type: ignore[arg-type]

    with pytest.raises(NotFound):
        await get_or_extract_section(
            materials=materials,
            sections=sections,
            storage=FakeStorage(),
            extractor=FakeExtractor(),
            embedder=FakeEmbedder(),
            vector_store=FakeVectorStore(),
            settings=settings,
            owner_id=owner,
            material_id=material_id,
            node_id="does-not-exist",
        )
