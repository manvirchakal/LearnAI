"""Generated study artifacts (narrative, game idea/code, diagrams) —
cached per collection, per kind, per content fingerprint (see
``services/generation/fingerprint.py``). Regenerating with the same
inputs (same collection content, same learning profile) is a cache hit
rather than a fresh, paid LLM call; changing either invalidates it since
the fingerprint changes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from bson import ObjectId

from learnai.repositories.base import ScopedRepository

ArtifactKind = Literal["narrative", "game", "diagrams"]


class ArtifactRepository(ScopedRepository[dict[str, Any]]):
    COLLECTION = "artifacts"

    async def get(
        self, collection_id: ObjectId, kind: ArtifactKind, fingerprint: str
    ) -> dict[str, Any] | None:
        return await self.find_one(
            {"collection_id": collection_id, "kind": kind, "fingerprint": fingerprint}
        )

    async def upsert(
        self,
        collection_id: ObjectId,
        kind: ArtifactKind,
        fingerprint: str,
        content: dict[str, Any],
    ) -> None:
        now = datetime.now(UTC)
        await self.update_one(
            {"collection_id": collection_id, "kind": kind, "fingerprint": fingerprint},
            {"$set": {"content": content, "updated_at": now}, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
