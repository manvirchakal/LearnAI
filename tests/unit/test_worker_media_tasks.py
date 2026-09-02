"""``transcribe_lecture_task``/``import_youtube_task`` against fakes — no
real Mongo, Redis, storage, faster-whisper model, or yt-dlp network call.
Mirrors ``test_worker_tasks.py``'s pattern for ``extract_toc_task``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from bson import ObjectId

from learnai.config import Settings
from learnai.repositories.jobs import JobRepository
from learnai.repositories.materials import MaterialRepository
from learnai.repositories.sections import SectionRepository
from learnai.services.asr import TranscriptResult, TranscriptSegment
from learnai.worker.tasks import import_youtube_task, transcribe_lecture_task
from tests.fakes.asr import FakeASR
from tests.fakes.embedder import FakeEmbedder
from tests.fakes.mongo import FakeAsyncDatabase
from tests.fakes.storage import FakeStorage
from tests.fakes.vector_store import FakeVectorStore


@pytest.fixture
def db() -> FakeAsyncDatabase:
    return FakeAsyncDatabase()


def _ctx(db: FakeAsyncDatabase, storage: FakeStorage, asr: FakeASR) -> dict[str, Any]:
    return {
        "db": db,
        "storage": storage,
        "asr": asr,
        "embedder": FakeEmbedder(),
        "vector_store": FakeVectorStore(),
        "settings": Settings(),
    }


_TRANSCRIPT = TranscriptResult(
    language="en",
    segments=[
        TranscriptSegment(start=0.0, end=2.0, text="Hello everyone."),
        TranscriptSegment(start=2.0, end=5.0, text="Today: limits."),
    ],
)


async def test_transcribe_lecture_happy_path(db: FakeAsyncDatabase) -> None:
    owner = ObjectId()
    materials = MaterialRepository(db, owner)  # type: ignore[arg-type]
    sections = SectionRepository(db, owner)  # type: ignore[arg-type]
    jobs = JobRepository(db, owner)  # type: ignore[arg-type]

    material_id = await materials.create(
        filename="lecture1.mp3",
        content_type="audio/mpeg",
        storage_key="media/owner/lecture1.mp3",
        size_bytes=1024,
        kind="lecture",
    )
    job_id = await jobs.create(kind="lecture_transcription", payload={})

    storage = FakeStorage()
    await storage.put("media/owner/lecture1.mp3", b"fake-audio-bytes", "audio/mpeg")
    asr = FakeASR(result=_TRANSCRIPT)
    ctx = _ctx(db, storage, asr)

    await transcribe_lecture_task(
        ctx, owner_id=str(owner), material_id=str(material_id), job_id=str(job_id)
    )

    material = await materials.get(material_id)
    assert material["status"] == "toc_ready"
    assert len(material["tree"]["tree"]) == 1
    assert "lecture1.mp3" in material["tree"]["tree"][0]["title"]

    section = await sections.get(material_id, "1")
    assert section is not None
    assert section["text"] == "Hello everyone. Today: limits."

    job = await jobs.get(job_id)
    assert job["status"] == "succeeded"
    assert asr.calls  # transcribe was actually called


async def test_transcribe_lecture_failure_marks_material_and_job_failed(
    db: FakeAsyncDatabase,
) -> None:
    owner = ObjectId()
    materials = MaterialRepository(db, owner)  # type: ignore[arg-type]
    jobs = JobRepository(db, owner)  # type: ignore[arg-type]

    material_id = await materials.create(
        filename="lecture1.mp3",
        content_type="audio/mpeg",
        storage_key="media/owner/missing.mp3",  # never put into storage -> StorageError
        size_bytes=1024,
        kind="lecture",
    )
    job_id = await jobs.create(kind="lecture_transcription", payload={})

    ctx = _ctx(db, FakeStorage(), FakeASR(result=_TRANSCRIPT))

    await transcribe_lecture_task(
        ctx, owner_id=str(owner), material_id=str(material_id), job_id=str(job_id)
    )

    material = await materials.get(material_id)
    assert material["status"] == "toc_failed"

    job = await jobs.get(job_id)
    assert job["status"] == "failed"


async def test_import_youtube_happy_path(db: FakeAsyncDatabase, tmp_path: Path) -> None:
    owner = ObjectId()
    materials = MaterialRepository(db, owner)  # type: ignore[arg-type]
    sections = SectionRepository(db, owner)  # type: ignore[arg-type]
    jobs = JobRepository(db, owner)  # type: ignore[arg-type]

    # routers/media.py creates this placeholder row before the download.
    material_id = await materials.create(
        filename="https://youtube.com/watch?v=abc123",
        content_type="audio/mp4",
        storage_key="youtube:https://youtube.com/watch?v=abc123",
        size_bytes=0,
        kind="lecture",
    )
    job_id = await jobs.create(kind="youtube_import", payload={})

    downloaded_path = tmp_path / "abc123.mp3"
    downloaded_path.write_bytes(b"fake-mp3-bytes")

    ctx = _ctx(db, FakeStorage(), FakeASR(result=_TRANSCRIPT))

    with patch(
        "learnai.worker.tasks.download_audio",
        return_value=("Lecture 1: Limits", downloaded_path),
    ):
        await import_youtube_task(
            ctx,
            owner_id=str(owner),
            material_id=str(material_id),
            job_id=str(job_id),
            url="https://youtube.com/watch?v=abc123",
        )

    material = await materials.get(material_id)
    assert material["status"] == "toc_ready"
    assert material["filename"] == "Lecture 1: Limits.mp3"
    assert material["content_type"] == "audio/mpeg"
    assert material["size_bytes"] == len(b"fake-mp3-bytes")

    storage: FakeStorage = ctx["storage"]
    assert await storage.get(material["storage_key"]) == b"fake-mp3-bytes"

    section = await sections.get(material_id, "1")
    assert section is not None

    job = await jobs.get(job_id)
    assert job["status"] == "succeeded"


async def test_import_youtube_download_failure_marks_material_and_job_failed(
    db: FakeAsyncDatabase,
) -> None:
    owner = ObjectId()
    materials = MaterialRepository(db, owner)  # type: ignore[arg-type]
    jobs = JobRepository(db, owner)  # type: ignore[arg-type]

    material_id = await materials.create(
        filename="https://youtube.com/watch?v=broken",
        content_type="audio/mp4",
        storage_key="youtube:https://youtube.com/watch?v=broken",
        size_bytes=0,
        kind="lecture",
    )
    job_id = await jobs.create(kind="youtube_import", payload={})

    ctx = _ctx(db, FakeStorage(), FakeASR(result=_TRANSCRIPT))

    with patch(
        "learnai.worker.tasks.download_audio", side_effect=RuntimeError("video unavailable")
    ):
        await import_youtube_task(
            ctx,
            owner_id=str(owner),
            material_id=str(material_id),
            job_id=str(job_id),
            url="https://youtube.com/watch?v=broken",
        )

    material = await materials.get(material_id)
    assert material["status"] == "toc_failed"
    assert material["error"] == "video unavailable"

    job = await jobs.get(job_id)
    assert job["status"] == "failed"
