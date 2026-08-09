"""Chat messages — one document per message, replacing the old design's
whole-conversation JSON blob. ``seq`` is allocated by
``ConversationRepository.next_seq`` before ``append`` is called; this
repository only ever inserts, never read-modify-writes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from learnai.repositories.base import ScopedRepository
from learnai.schemas.chat import ChatCitation, ChatRole


class ChatMessageRepository(ScopedRepository[dict[str, Any]]):
    COLLECTION = "chat_messages"

    async def append(
        self,
        *,
        conversation_id: ObjectId,
        seq: int,
        role: ChatRole,
        content: str,
        citations: list[ChatCitation] | None = None,
    ) -> dict[str, Any]:
        doc = {
            "conversation_id": conversation_id,
            "seq": seq,
            "role": role,
            "content": content,
            "citations": [c.model_dump(mode="json") for c in citations or []],
            "created_at": datetime.now(UTC),
        }
        message_id = await self.insert_one(doc)
        return {**doc, "_id": message_id, "owner_id": self.owner_id}

    async def list_for_conversation(self, conversation_id: ObjectId) -> list[dict[str, Any]]:
        return [
            doc async for doc in self.find({"conversation_id": conversation_id}, sort=[("seq", 1)])
        ]
