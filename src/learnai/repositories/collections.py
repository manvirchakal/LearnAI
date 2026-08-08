"""Collections — replaces ``collections/{user}/{cid}.json`` in S3.

``parent_collection_id`` is the fix for the old orphaned-ID bug: the
original ``create_textbook_collections`` generated section collections with
``collection_id = section_id = uuid4()``, then built the parent chapter
collection's ``materials.textbook_sections`` entries with a *different*,
freshly-generated ``uuid4()`` for those same sections — so a chapter
collection referenced section IDs that existed nowhere. Here, a section
collection just carries a real ``parent_collection_id`` pointing at its
chapter, set once at creation, queryable directly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from bson import ObjectId

from learnai.errors import NotFound
from learnai.repositories.base import ScopedRepository

CollectionKind = Literal["auto", "manual", "chapter", "section"]


class CollectionRepository(ScopedRepository[dict[str, Any]]):
    COLLECTION = "collections"

    async def create(
        self,
        *,
        name: str,
        kind: CollectionKind,
        parent_collection_id: ObjectId | None = None,
        material_refs: list[dict[str, Any]] | None = None,
    ) -> ObjectId:
        now = datetime.now(UTC)
        return await self.insert_one(
            {
                "name": name,
                "kind": kind,
                "parent_collection_id": parent_collection_id,
                "material_refs": material_refs or [],
                "created_at": now,
                "updated_at": now,
            }
        )

    async def list_all(self) -> list[dict[str, Any]]:
        # Newest first — matches the {owner_id:1, created_at:-1} index from
        # db/migrations, so this is an index-covered sort, not an in-memory one.
        return [doc async for doc in self.find({}, sort=[("created_at", -1)])]

    async def get(self, collection_id: ObjectId) -> dict[str, Any]:
        doc = await self.find_one({"_id": collection_id})
        if doc is None:
            raise NotFound(f"collection {collection_id} not found")
        return doc

    async def update_materials(
        self, collection_id: ObjectId, material_refs: list[dict[str, Any]]
    ) -> None:
        result = await self.update_one(
            {"_id": collection_id},
            {"$set": {"material_refs": material_refs, "updated_at": datetime.now(UTC)}},
        )
        if result.matched_count == 0:
            raise NotFound(f"collection {collection_id} not found")

    async def list_children(self, parent_collection_id: ObjectId) -> list[dict[str, Any]]:
        return [doc async for doc in self.find({"parent_collection_id": parent_collection_id})]
