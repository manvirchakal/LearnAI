"""Index for the ``translations`` cache — Phase 7's translation service."""

from __future__ import annotations

from learnai.db.mongo import Database

MIGRATION_ID = "0006_translations_indexes"


async def apply(db: Database) -> None:
    # The cache key: one document per (owner, text_hash, target_language) —
    # looked up before every translate() call, written at most once per
    # distinct (owner, source text, target language) triple.
    await db["translations"].create_index(
        [("owner_id", 1), ("text_hash", 1), ("target_language", 1)], unique=True
    )
