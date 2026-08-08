"""Registry of migrations, in application order. Add new modules here as
new collections/indexes are introduced — never edit an already-applied
migration's ``apply()``; add a new one instead.
"""

from __future__ import annotations

from learnai.db.migrations import m0001_initial_indexes, m0002_materials_and_sections_indexes
from learnai.db.migrations._runner import Migration, apply_pending

ALL_MIGRATIONS: list[Migration] = [m0001_initial_indexes, m0002_materials_and_sections_indexes]

__all__ = ["ALL_MIGRATIONS", "apply_pending"]
