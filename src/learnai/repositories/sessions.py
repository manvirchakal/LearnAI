"""Refresh-token sessions.

Looked up by ``token_hash`` — never by owner, since presenting the token
*is* how we discover who it belongs to. Refresh tokens rotate on every use;
``family_id`` links every token descended from one login, so a reused
(already-rotated-away) token can revoke the whole chain rather than just
itself — the standard defense against a stolen refresh token being replayed
after the legitimate client has already rotated past it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId

from learnai.db.mongo import Database


class SessionRepository:
    COLLECTION = "sessions"

    def __init__(self, db: Database) -> None:
        self._collection = db[self.COLLECTION]

    async def create(
        self,
        *,
        owner_id: ObjectId,
        token_hash: str,
        family_id: str,
        user_agent: str | None,
        ip: str | None,
        created_at: datetime,
        expires_at: datetime,
    ) -> ObjectId:
        result = await self._collection.insert_one(
            {
                "owner_id": owner_id,
                "token_hash": token_hash,
                "family_id": family_id,
                "user_agent": user_agent,
                "ip": ip,
                "created_at": created_at,
                "expires_at": expires_at,
                "revoked_at": None,
            }
        )
        inserted_id: ObjectId = result.inserted_id
        return inserted_id

    async def find_by_token_hash(self, token_hash: str) -> dict[str, Any] | None:
        return await self._collection.find_one({"token_hash": token_hash})

    async def revoke(self, session_id: ObjectId, *, revoked_at: datetime) -> None:
        await self._collection.update_one({"_id": session_id}, {"$set": {"revoked_at": revoked_at}})

    async def revoke_family(self, family_id: str, *, revoked_at: datetime) -> None:
        """Reuse detected (or explicit logout-everywhere): revoke every
        token descended from this login, not just the one presented."""
        await self._collection.update_many(
            {"family_id": family_id, "revoked_at": None}, {"$set": {"revoked_at": revoked_at}}
        )
