"""Users — the one collection that can't be owner-scoped, since a user *is*
the owner concept everything else scopes against. Looked up by Google
``sub`` at login (before we know who's asking) and by ``_id`` everywhere
after.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument

from learnai.db.mongo import Database


class UserRepository:
    COLLECTION = "users"

    def __init__(self, db: Database) -> None:
        self._collection = db[self.COLLECTION]

    async def find_by_id(self, user_id: ObjectId) -> dict[str, Any] | None:
        return await self._collection.find_one({"_id": user_id})

    async def find_by_google_sub(self, google_sub: str) -> dict[str, Any] | None:
        return await self._collection.find_one({"google_sub": google_sub})

    async def upsert_from_google(
        self, *, google_sub: str, email: str, email_verified: bool, name: str, picture: str | None
    ) -> dict[str, Any]:
        """First login creates the user; every login refreshes the profile
        fields Google may have changed (name, picture) and touches
        last_login_at. Atomic: one round trip, returns the post-upsert
        document directly rather than updating then re-fetching."""
        now = datetime.now(UTC)
        user = await self._collection.find_one_and_update(
            {"google_sub": google_sub},
            {
                "$set": {
                    "email": email,
                    "email_verified": email_verified,
                    "name": name,
                    "picture": picture,
                    "last_login_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        # find_one_and_update's return type is Optional because that's true
        # in general (e.g. no match, upsert=False) — with upsert=True and
        # return_document=AFTER specifically, MongoDB guarantees a document
        # comes back: either the matched one, updated, or the newly-created one.
        if user is None:  # pragma: no cover - unreachable per the guarantee above
            raise RuntimeError("find_one_and_update(upsert=True, AFTER) returned None")
        return user
