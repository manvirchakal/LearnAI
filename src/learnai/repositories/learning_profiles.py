"""One learning-profile document per user — replaces
``learning_profiles/{user_id}.json`` in S3.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from learnai.repositories.base import ScopedRepository


class LearningProfileRepository(ScopedRepository[dict[str, Any]]):
    COLLECTION = "learning_profiles"

    async def get(self) -> dict[str, Any] | None:
        return await self.find_one({})

    async def upsert(
        self,
        *,
        answers: dict[str, list[Any]],
        scores: dict[str, float],
        description: str,
        questionnaire_version: int,
    ) -> None:
        """Created on first questionnaire submission, replaced wholesale on
        a retake — there is exactly one profile per owner (see the unique
        index on owner_id in db/migrations)."""
        now = datetime.now(UTC)
        await self.update_one(
            {},
            {
                "$set": {
                    "answers": answers,
                    "scores": scores,
                    "description": description,
                    "questionnaire_version": questionnaire_version,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
