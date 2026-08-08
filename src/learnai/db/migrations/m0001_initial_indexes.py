"""Indexes for the collections Phase 1 introduces: users, sessions,
learning_profiles, collections.
"""

from __future__ import annotations

from learnai.db.mongo import Database

MIGRATION_ID = "0001_initial_indexes"


async def apply(db: Database) -> None:
    await db["users"].create_index("google_sub", unique=True)
    await db["users"].create_index("email", unique=True)

    await db["learning_profiles"].create_index("owner_id", unique=True)

    await db["collections"].create_index([("owner_id", 1), ("created_at", -1)])
    await db["collections"].create_index("parent_collection_id")

    await db["sessions"].create_index("token_hash", unique=True)
    # TTL index: Mongo deletes the document once expires_at is in the past —
    # no separate cleanup job needed for expired refresh tokens.
    await db["sessions"].create_index("expires_at", expireAfterSeconds=0)
    await db["sessions"].create_index("family_id")
