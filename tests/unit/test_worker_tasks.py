"""``extract_toc_task`` against fakes — no real Mongo, Redis, storage, or
Anthropic call. Exercises the same job/material state machine the real
worker drives, just with an in-memory database and a scripted extractor.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pymupdf
import pytest
from bson import ObjectId

from learnai.errors import UpstreamError
from learnai.repositories.jobs import JobRepository
from learnai.repositories.materials import MaterialRepository
from learnai.schemas.documents import SectionContent, TOCResult, TreeNode
from learnai.services.extraction.base import DocRef
from learnai.worker.tasks import extract_toc_task
from tests.fakes.mongo import FakeAsyncDatabase


def _make_pdf(num_pages: int) -> bytes:
    doc = pymupdf.open()  # type: ignore[no-untyped-call]
    for _ in range(num_pages):
        doc.new_page()
    buffer: bytes = doc.tobytes()  # type: ignore[no-untyped-call]
    doc.close()  # type: ignore[no-untyped-call]
    return buffer


class FakeStorage:
    def __init__(self, blobs: dict[str, bytes]) -> None:
        self._blobs = blobs

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        raise NotImplementedError

    async def get(self, key: str) -> bytes:
        return self._blobs[key]

    def open(self, key: str) -> AsyncIterator[bytes]:
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        raise NotImplementedError

    async def exists(self, key: str) -> bool:
        raise NotImplementedError


class FakeExtractor:
    def __init__(
        self, *, toc_result: TOCResult | None = None, raises: Exception | None = None
    ) -> None:
        self._toc_result = toc_result
        self._raises = raises
        self.uploaded: list[bytes] = []
        self.deleted: list[DocRef] = []

    async def upload(self, pdf_bytes: bytes, *, filename: str) -> DocRef:
        self.uploaded.append(pdf_bytes)
        return DocRef(file_id="file-123")

    async def delete(self, ref: DocRef) -> None:
        self.deleted.append(ref)

    async def extract_toc(self, ref: DocRef, *, page_offset: int = 0) -> TOCResult:
        if self._raises is not None:
            raise self._raises
        assert self._toc_result is not None
        return self._toc_result

    async def extract_section(
        self, ref: DocRef, *, node_id: str, page_offset: int = 0
    ) -> SectionContent:
        raise NotImplementedError


@pytest.fixture
def db() -> FakeAsyncDatabase:
    return FakeAsyncDatabase()


async def _seed_material(db: FakeAsyncDatabase, owner: ObjectId) -> ObjectId:
    materials = MaterialRepository(db, owner)  # type: ignore[arg-type]
    return await materials.create(
        filename="calculus.pdf",
        content_type="application/pdf",
        storage_key="materials/calculus.pdf",
        size_bytes=1024,
    )


async def test_happy_path_stores_tree_and_marks_ready(db: FakeAsyncDatabase) -> None:
    owner = ObjectId()
    material_id = await _seed_material(db, owner)
    jobs = JobRepository(db, owner)  # type: ignore[arg-type]
    job_id = await jobs.create(kind="toc_extraction", payload={"material_id": str(material_id)})

    toc_result = TOCResult(
        tree=[TreeNode(node_id="1", title="Chapter 1", start_page=1, end_page=5)],
        confidence="high",
    )
    extractor = FakeExtractor(toc_result=toc_result)
    ctx: dict[str, Any] = {
        "db": db,
        "storage": FakeStorage({"materials/calculus.pdf": _make_pdf(5)}),
        "extractor": extractor,
    }

    await extract_toc_task(
        ctx, owner_id=str(owner), material_id=str(material_id), job_id=str(job_id)
    )

    materials = MaterialRepository(db, owner)  # type: ignore[arg-type]
    material = await materials.get(material_id)
    assert material["status"] == "toc_ready"
    assert material["page_count"] == 5
    assert material["tree"]["tree"][0]["title"] == "Chapter 1"

    job = await jobs.get(job_id)
    assert job["status"] == "succeeded"

    # The upload was scoped to a sliced excerpt, and cleaned up afterward.
    assert len(extractor.uploaded) == 1
    assert len(extractor.deleted) == 1


async def test_extraction_failure_marks_material_and_job_failed(db: FakeAsyncDatabase) -> None:
    owner = ObjectId()
    material_id = await _seed_material(db, owner)
    jobs = JobRepository(db, owner)  # type: ignore[arg-type]
    job_id = await jobs.create(kind="toc_extraction", payload={"material_id": str(material_id)})

    extractor = FakeExtractor(raises=UpstreamError("Anthropic declined the TOC request"))
    ctx: dict[str, Any] = {
        "db": db,
        "storage": FakeStorage({"materials/calculus.pdf": _make_pdf(3)}),
        "extractor": extractor,
    }

    await extract_toc_task(
        ctx, owner_id=str(owner), material_id=str(material_id), job_id=str(job_id)
    )

    materials = MaterialRepository(db, owner)  # type: ignore[arg-type]
    material = await materials.get(material_id)
    assert material["status"] == "toc_failed"
    assert material["error"] == "Anthropic declined the TOC request"

    job = await jobs.get(job_id)
    assert job["status"] == "failed"
    assert job["error"] == "Anthropic declined the TOC request"

    # The excerpt upload is still cleaned up even though extraction failed.
    assert len(extractor.deleted) == 1
