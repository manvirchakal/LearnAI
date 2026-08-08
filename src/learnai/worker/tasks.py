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
from typing import Any

from bson import ObjectId

from learnai.db.mongo import Database
from learnai.errors import NotFound
from learnai.logging import get_logger
from learnai.repositories.jobs import JobRepository
from learnai.repositories.materials import MaterialRepository
from learnai.services.extraction.base import DocumentExtractor
from learnai.services.ingestion.pdf import page_count, slice_pages
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
