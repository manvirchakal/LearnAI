"""Materials — an uploaded source document an owner can extract a table
of contents and sections from. Raw bytes live in ``StorageBackend``; this
collection holds metadata, ingestion status, and (once processing
completes) the document tree.

Two kinds share this one collection rather than getting a parallel
schema: ``"pdf"`` (the original, TOC-extracted by
``worker.tasks.extract_toc_task``) and ``"lecture"`` (audio/video,
transcribed by ``worker.tasks.transcribe_lecture_task`` /
``import_youtube_task`` — see ``services/ingestion/media.py``). A lecture's
``tree`` is time-bucketed segments rather than page ranges, but it's the
same ``TOCResult``/``TreeNode`` shape, so every downstream consumer
(collections, generation, chat) needs zero changes to treat a transcribed
lecture exactly like a PDF's chapters. The ``status``/``tree`` field names
keep their PDF-era ``toc_*`` naming for both kinds rather than being
renamed generic — a lecture's "table of contents" is genuinely just its
segment list, and renaming would touch every call site for no behavioral
gain.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from bson import ObjectId

from learnai.errors import NotFound
from learnai.repositories.base import ScopedRepository
from learnai.schemas.documents import TOCResult

MaterialStatus = Literal["uploaded", "toc_processing", "toc_ready", "toc_failed"]
MaterialKind = Literal["pdf", "lecture"]


class MaterialRepository(ScopedRepository[dict[str, Any]]):
    COLLECTION = "materials"

    async def create(
        self,
        *,
        filename: str,
        content_type: str,
        storage_key: str,
        size_bytes: int,
        kind: MaterialKind = "pdf",
    ) -> ObjectId:
        now = datetime.now(UTC)
        return await self.insert_one(
            {
                "filename": filename,
                "content_type": content_type,
                "storage_key": storage_key,
                "size_bytes": size_bytes,
                "kind": kind,
                "status": "uploaded",
                "page_count": None,
                "tree": None,
                "error": None,
                "created_at": now,
                "updated_at": now,
            }
        )

    async def update_source(
        self,
        material_id: ObjectId,
        *,
        filename: str,
        content_type: str,
        storage_key: str,
        size_bytes: int,
    ) -> None:
        """Fills in the real file metadata once it's known — used by
        ``import_youtube_task``, which creates the material row before the
        download (so the router can return ``202`` without blocking on a
        slow yt-dlp fetch) and only learns the real filename/size after."""
        result = await self.update_one(
            {"_id": material_id},
            {
                "$set": {
                    "filename": filename,
                    "content_type": content_type,
                    "storage_key": storage_key,
                    "size_bytes": size_bytes,
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        if result.matched_count == 0:
            raise NotFound(f"material {material_id} not found")

    async def get(self, material_id: ObjectId) -> dict[str, Any]:
        doc = await self.find_one({"_id": material_id})
        if doc is None:
            raise NotFound(f"material {material_id} not found")
        return doc

    async def list_all(self) -> list[dict[str, Any]]:
        return [doc async for doc in self.find({}, sort=[("created_at", -1)])]

    async def mark_toc_processing(self, material_id: ObjectId, *, page_count: int) -> None:
        result = await self.update_one(
            {"_id": material_id},
            {
                "$set": {
                    "status": "toc_processing",
                    "page_count": page_count,
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        if result.matched_count == 0:
            raise NotFound(f"material {material_id} not found")

    async def set_toc_result(self, material_id: ObjectId, tree: TOCResult) -> None:
        result = await self.update_one(
            {"_id": material_id},
            {
                "$set": {
                    "status": "toc_ready",
                    "tree": tree.model_dump(mode="json"),
                    "error": None,
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        if result.matched_count == 0:
            raise NotFound(f"material {material_id} not found")

    async def mark_toc_failed(self, material_id: ObjectId, *, error: str) -> None:
        result = await self.update_one(
            {"_id": material_id},
            {"$set": {"status": "toc_failed", "error": error, "updated_at": datetime.now(UTC)}},
        )
        if result.matched_count == 0:
            raise NotFound(f"material {material_id} not found")
