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

    async def get_latest(
        self, collection_id: ObjectId, kind: ArtifactKind
    ) -> dict[str, Any] | None:
        """The most recently generated artifact of this kind, regardless of
        fingerprint — what the chat agent's ``get_narrative`` tool reads,
        since it wants whatever narrative already exists for the
        collection, not one tied to a specific set of inputs."""
        docs = [
            doc
            async for doc in self.find(
                {"collection_id": collection_id, "kind": kind}, sort=[("updated_at", -1)]
            )
        ]
        return docs[0] if docs else None

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
