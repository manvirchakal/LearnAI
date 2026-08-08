"""Tiny numbered-migration runner.

Each migration module exposes ``MIGRATION_ID`` (a stable string) and an
``async def apply(db) -> None``. Applied IDs are tracked in a ``_migrations``
collection so re-running is a no-op — safe to call on every process start.

This only needs to handle index creation for now, which is itself idempotent
(``create_index`` on an already-existing equivalent index is a no-op), so a
duplicate-key race between two API replicas booting simultaneously is
harmless: whichever loses just finds its ``_migrations`` insert rejected and
moves on, having already (redundantly, harmlessly) recreated the same
indexes.
"""

from __future__ import annotations

import contextlib
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol

from pymongo.errors import DuplicateKeyError

from learnai.db.mongo import Database
from learnai.logging import get_logger

logger = get_logger(__name__)

MIGRATIONS_COLLECTION = "_migrations"


class Migration(Protocol):
    MIGRATION_ID: str

    async def apply(self, db: Database) -> None: ...


async def apply_pending(db: Database, migrations: Sequence[Migration]) -> list[str]:
    applied_ids = {doc["_id"] async for doc in db[MIGRATIONS_COLLECTION].find({})}

    newly_applied: list[str] = []
    for migration in migrations:
        if migration.MIGRATION_ID in applied_ids:
            continue
        await migration.apply(db)
        # Another process may have applied (and recorded) this migration
        # first, between our membership check and this insert — the apply()
        # above was redundant but harmless in that case; see module docstring.
        with contextlib.suppress(DuplicateKeyError):
            await db[MIGRATIONS_COLLECTION].insert_one(
                {"_id": migration.MIGRATION_ID, "applied_at": datetime.now(UTC)}
            )
        newly_applied.append(migration.MIGRATION_ID)
        logger.info("migration_applied", migration_id=migration.MIGRATION_ID)

    return newly_applied
