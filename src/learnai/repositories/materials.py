"""Materials — an uploaded source document (a PDF) an owner can extract a
table of contents and sections from. Raw bytes live in ``StorageBackend``;
this collection holds metadata, ingestion status, and (once the TOC pass
completes) the document tree.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from bson import ObjectId

from learnai.errors import NotFound
from learnai.repositories.base import ScopedRepository
from learnai.schemas.documents import TOCResult

MaterialStatus = Literal["uploaded", "toc_processing", "toc_ready", "toc_failed"]


class MaterialRepository(ScopedRepository[dict[str, Any]]):
    COLLECTION = "materials"

    async def create(
        self, *, filename: str, content_type: str, storage_key: str, size_bytes: int
    ) -> ObjectId:
        now = datetime.now(UTC)
        return await self.insert_one(
            {
                "filename": filename,
                "content_type": content_type,
                "storage_key": storage_key,
                "size_bytes": size_bytes,
                "status": "uploaded",
                "page_count": None,
                "tree": None,
                "error": None,
                "created_at": now,
                "updated_at": now,
            }
        )

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
