"""Indexes for the ``artifacts`` collection Phase 5 introduces."""

from __future__ import annotations

from learnai.db.mongo import Database

MIGRATION_ID = "0004_artifacts_indexes"


async def apply(db: Database) -> None:
    # The cache key: one document per (owner, collection, kind, fingerprint) —
    # looked up before every generation call, written at most once per
    # distinct set of inputs (see ArtifactRepository.upsert).
    await db["artifacts"].create_index(
        [("owner_id", 1), ("collection_id", 1), ("kind", 1), ("fingerprint", 1)], unique=True
    )
