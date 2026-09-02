"""ARQ task functions, run by the worker process (see ``worker/settings.py``).

Each task is handed its dependencies through ``ctx`` — built once in
``WorkerSettings.on_startup``, not per-job — mirroring how ``main.py``'s
``lifespan`` builds the API process's singletons. The worker is a separate
process from the API, so it cannot reach ``app.state``; ``ctx`` is its
equivalent.

Broad ``except Exception`` is deliberately allowed here (see the per-file
ruff ignore in ``pyproject.toml``) — a task is the boundary: any failure,
typed or not, must be recorded on the job/material rather than crash the
worker or vanish into ARQ's own retry logic silently re-spending Anthropic
credits on the same broken input.
"""

from __future__ import annotations

import contextlib
import tempfile
import uuid
from pathlib import Path
from typing import Any

from bson import ObjectId

from learnai.config import Settings
from learnai.db.mongo import Database
from learnai.errors import NotFound
from learnai.logging import get_logger
from learnai.repositories.jobs import JobRepository
from learnai.repositories.materials import MaterialRepository
from learnai.repositories.sections import SectionRepository
from learnai.services.asr import ASREngine, TranscriptResult
from learnai.services.extraction.base import DocumentExtractor
from learnai.services.ingestion.media import group_transcript_into_tree
from learnai.services.ingestion.pdf import page_count, slice_pages
from learnai.services.ingestion.pipeline import index_section
from learnai.services.ingestion.youtube import download_audio
from learnai.services.retrieval.embedder import Embedder
from learnai.services.retrieval.vector_store import VectorStore
from learnai.services.storage.base import StorageBackend

logger = get_logger(__name__)

# The TOC pass only needs to see the front matter — sending the whole book
# would defeat the point of a cheap, upload-time structure pass (see the
# lazy-per-section-extraction cost mitigation in the modernization plan).
TOC_EXCERPT_PAGES = 20


async def extract_toc_task(
    ctx: dict[str, Any], *, owner_id: str, material_id: str, job_id: str
) -> None:
    db: Database = ctx["db"]
    storage: StorageBackend = ctx["storage"]
    extractor: DocumentExtractor = ctx["extractor"]

    owner = ObjectId(owner_id)
    materials = MaterialRepository(db, owner)
    jobs = JobRepository(db, owner)
    material_oid = ObjectId(material_id)
    job_oid = ObjectId(job_id)

    try:
        await jobs.mark_running(job_oid)
        material = await materials.get(material_oid)
        pdf_bytes = await storage.get(material["storage_key"])

        total_pages = page_count(pdf_bytes)
        await materials.mark_toc_processing(material_oid, page_count=total_pages)

        excerpt_end = min(total_pages, TOC_EXCERPT_PAGES)
        excerpt = slice_pages(pdf_bytes, start_page=1, end_page=excerpt_end)

        ref = await extractor.upload(excerpt, filename=material["filename"])
        try:
            toc = await extractor.extract_toc(ref)
        finally:
            await extractor.delete(ref)

        await materials.set_toc_result(material_oid, toc)
        await jobs.mark_succeeded(job_oid)
    except Exception as exc:
        logger.error("toc_extraction_failed", material_id=material_id, job_id=job_id, exc_info=True)
        error = str(exc)
        with contextlib.suppress(NotFound):  # the material itself is gone; nothing to annotate
            await materials.mark_toc_failed(material_oid, error=error)
        await jobs.mark_failed(job_oid, error=error)


async def _store_transcript(
    *,
    transcript: TranscriptResult,
    title: str,
    materials: MaterialRepository,
    sections: SectionRepository,
    embedder: Embedder,
    vector_store: VectorStore,
    settings: Settings,
    owner_id: ObjectId,
    material_id: ObjectId,
) -> None:
    """Shared by ``transcribe_lecture_task`` and ``import_youtube_task``:
    turns a transcript into a document tree, upserts every section, and
    indexes it. Indexing happens eagerly here (unlike a PDF's lazy,
    read-time indexing in ``get_or_extract_section``) since transcription
    is already the expensive one-time step — there's no cost-mitigation
    reason left to defer it."""
    tree, section_contents = group_transcript_into_tree(transcript, title=title)
    await materials.set_toc_result(material_id, tree)

    for node, content in zip(tree.tree, section_contents, strict=True):
        await sections.upsert(material_id, content)
        try:
            await index_section(
                content,
                material_id=material_id,
                node=node,
                node_path=[node.node_id],
                embedder=embedder,
                vector_store=vector_store,
                settings=settings,
                owner_id=owner_id,
            )
        except Exception:
            # Same reasoning as get_or_extract_section: indexing is a
            # search-quality enhancement, not part of the transcription
            # job's correctness.
            logger.error(
                "lecture_section_indexing_failed",
                material_id=str(material_id),
                node_id=node.node_id,
                exc_info=True,
            )


async def transcribe_lecture_task(
    ctx: dict[str, Any], *, owner_id: str, material_id: str, job_id: str
) -> None:
    """Transcribes a directly-uploaded lecture (audio/video already in
    ``StorageBackend``, see ``routers/media.py``). faster-whisper decodes
    the file itself (via PyAV/ffmpeg internally) — no separate transcoding
    step is needed regardless of the source format."""
    db: Database = ctx["db"]
    storage: StorageBackend = ctx["storage"]
    asr: ASREngine = ctx["asr"]
    embedder: Embedder = ctx["embedder"]
    vector_store: VectorStore = ctx["vector_store"]
    settings: Settings = ctx["settings"]

    owner = ObjectId(owner_id)
    materials = MaterialRepository(db, owner)
    sections = SectionRepository(db, owner)
    jobs = JobRepository(db, owner)
    material_oid = ObjectId(material_id)
    job_oid = ObjectId(job_id)

    try:
        await jobs.mark_running(job_oid)
        material = await materials.get(material_oid)
        await materials.mark_toc_processing(material_oid, page_count=0)

        audio_bytes = await storage.get(material["storage_key"])
        suffix = Path(material["filename"]).suffix or ".audio"
        with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            transcript = await asr.transcribe(Path(tmp.name))

        await _store_transcript(
            transcript=transcript,
            title=material["filename"],
            materials=materials,
            sections=sections,
            embedder=embedder,
            vector_store=vector_store,
            settings=settings,
            owner_id=owner,
            material_id=material_oid,
        )
        await jobs.mark_succeeded(job_oid, result={"material_id": str(material_oid)})
    except Exception as exc:
        logger.error(
            "lecture_transcription_failed", material_id=material_id, job_id=job_id, exc_info=True
        )
        error = str(exc)
        with contextlib.suppress(NotFound):
            await materials.mark_toc_failed(material_oid, error=error)
        await jobs.mark_failed(job_oid, error=error)


async def import_youtube_task(
    ctx: dict[str, Any], *, owner_id: str, material_id: str, job_id: str, url: str
) -> None:
    """Downloads a YouTube video's audio, persists it, and transcribes it.
    The material row already exists (created by ``routers/media.py`` with
    placeholder metadata so it can return ``202`` without blocking on the
    download) — this fills in the real filename/size once known."""
    db: Database = ctx["db"]
    storage: StorageBackend = ctx["storage"]
    asr: ASREngine = ctx["asr"]
    embedder: Embedder = ctx["embedder"]
    vector_store: VectorStore = ctx["vector_store"]
    settings: Settings = ctx["settings"]

    owner = ObjectId(owner_id)
    materials = MaterialRepository(db, owner)
    sections = SectionRepository(db, owner)
    jobs = JobRepository(db, owner)
    material_oid = ObjectId(material_id)
    job_oid = ObjectId(job_id)

    try:
        await jobs.mark_running(job_oid)
        with tempfile.TemporaryDirectory() as tmp_dir:
            title, audio_path = await download_audio(url, Path(tmp_dir))
            audio_bytes = audio_path.read_bytes()

            storage_key = f"media/{owner_id}/{uuid.uuid4().hex}.mp3"
            await storage.put(storage_key, audio_bytes, "audio/mpeg")
            await materials.update_source(
                material_oid,
                filename=f"{title}.mp3",
                content_type="audio/mpeg",
                storage_key=storage_key,
                size_bytes=len(audio_bytes),
            )
            await materials.mark_toc_processing(material_oid, page_count=0)

            transcript = await asr.transcribe(audio_path)

        await _store_transcript(
            transcript=transcript,
            title=title,
            materials=materials,
            sections=sections,
            embedder=embedder,
            vector_store=vector_store,
            settings=settings,
            owner_id=owner,
            material_id=material_oid,
        )
        await jobs.mark_succeeded(job_oid, result={"material_id": str(material_oid)})
    except Exception as exc:
        logger.error("youtube_import_failed", material_id=material_id, job_id=job_id, exc_info=True)
        error = str(exc)
        with contextlib.suppress(NotFound):
            await materials.mark_toc_failed(material_oid, error=error)
        await jobs.mark_failed(job_oid, error=error)
