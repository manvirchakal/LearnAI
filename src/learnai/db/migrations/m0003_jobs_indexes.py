"""Indexes for the ``jobs`` collection Phase 3 introduces."""

from __future__ import annotations

from learnai.db.mongo import Database

MIGRATION_ID = "0003_jobs_indexes"


async def apply(db: Database) -> None:
    await db["jobs"].create_index([("owner_id", 1), ("created_at", -1)])
