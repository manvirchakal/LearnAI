"""Sections — cached, lazily-extracted content for one node of a
material's document tree. Extracted once (see ``AnthropicPDFExtractor``)
the first time someone reads it, then served from here on every
subsequent read — turns the old eager-extract-everything-at-upload cost
into fractions of a cent per section actually studied.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from learnai.repositories.base import ScopedRepository
from learnai.schemas.documents import SectionContent


class SectionRepository(ScopedRepository[dict[str, Any]]):
    COLLECTION = "sections"

    async def get(self, material_id: ObjectId, node_id: str) -> dict[str, Any] | None:
        return await self.find_one({"material_id": material_id, "node_id": node_id})

    async def upsert(self, material_id: ObjectId, section: SectionContent) -> None:
        now = datetime.now(UTC)
        await self.update_one(
            {"material_id": material_id, "node_id": section.node_id},
            {
                "$set": {
                    "text": section.text,
                    "citations": [c.model_dump(mode="json") for c in section.citations],
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
