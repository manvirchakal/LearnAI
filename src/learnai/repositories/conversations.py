"""Conversations — one chat thread per (owner, collection). Owns the
atomic ``seq_counter`` ``ChatMessageRepository.append`` increments against,
replacing the old design's single JSON blob GET-modified-PUT per message
(``main.py:1284-1342``): O(n) bytes moved per message, lost updates under
concurrency, unpageable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from learnai.errors import NotFound
from learnai.repositories.base import ScopedRepository


class ConversationRepository(ScopedRepository[dict[str, Any]]):
    COLLECTION = "conversations"

    async def get_or_create(self, collection_id: ObjectId) -> dict[str, Any]:
        """Chat state is scoped to what the user is studying, not started
        fresh every visit — the first message in a collection creates its
        conversation, every later message reuses it."""
        existing = await self.find_one({"collection_id": collection_id})
        if existing is not None:
            return existing
        now = datetime.now(UTC)
        conversation_id = await self.insert_one(
            {
                "collection_id": collection_id,
                "seq_counter": 0,
                "created_at": now,
                "updated_at": now,
            }
        )
        return await self.get(conversation_id)

    async def get(self, conversation_id: ObjectId) -> dict[str, Any]:
        doc = await self.find_one({"_id": conversation_id})
        if doc is None:
            raise NotFound(f"conversation {conversation_id} not found")
        return doc

    async def next_seq(self, conversation_id: ObjectId) -> int:
        """Atomically allocate the next message sequence number. One round
        trip, no read-modify-write — concurrent callers each get a distinct,
        gapless increment, enforced further by the unique
        ``(owner_id, conversation_id, seq)`` index on ``chat_messages``."""
        doc = await self.find_one_and_update(
            {"_id": conversation_id},
            {"$inc": {"seq_counter": 1}, "$set": {"updated_at": datetime.now(UTC)}},
            return_document=True,
        )
        if doc is None:
            raise NotFound(f"conversation {conversation_id} not found")
        seq: int = doc["seq_counter"]
        return seq
