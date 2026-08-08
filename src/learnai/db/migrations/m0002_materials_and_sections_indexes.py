"""Indexes for the collections Phase 3 introduces: materials, sections."""

from __future__ import annotations

from learnai.db.mongo import Database

MIGRATION_ID = "0002_materials_and_sections_indexes"


async def apply(db: Database) -> None:
    await db["materials"].create_index([("owner_id", 1), ("created_at", -1)])

    # The cache key for lazily-extracted section content: one document per
    # (owner, material, node), looked up on every section read and written
    # at most once per section (see SectionRepository.upsert).
    await db["sections"].create_index(
        [("owner_id", 1), ("material_id", 1), ("node_id", 1)], unique=True
    )
