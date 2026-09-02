"""Translation cache — content-addressed by ``sha256(text)`` + target
language. The fix for the old design's ``translate_text`` helper
(``server/main.py``), which had no caching at all and re-hit AWS
Translate on every single call, including the same narrative translated
repeatedly on every page load.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from learnai.repositories.base import ScopedRepository


class TranslationRepository(ScopedRepository[dict[str, Any]]):
    COLLECTION = "translations"

    async def get(self, text_hash: str, target_language: str) -> str | None:
        doc = await self.find_one({"text_hash": text_hash, "target_language": target_language})
        return doc["translated_text"] if doc is not None else None

    async def upsert(self, text_hash: str, target_language: str, translated_text: str) -> None:
        now = datetime.now(UTC)
        await self.update_one(
            {"text_hash": text_hash, "target_language": target_language},
            {
                "$set": {"translated_text": translated_text, "updated_at": now},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
