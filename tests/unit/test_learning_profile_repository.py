from __future__ import annotations

import pytest
from bson import ObjectId

from learnai.repositories.learning_profiles import LearningProfileRepository
from tests.fakes.mongo import FakeAsyncDatabase


@pytest.fixture
def db() -> FakeAsyncDatabase:
    return FakeAsyncDatabase()


async def test_get_returns_none_before_any_submission(db: FakeAsyncDatabase) -> None:
    repo = LearningProfileRepository(db, ObjectId())  # type: ignore[arg-type]
    assert await repo.get() is None


async def test_upsert_creates_then_get_returns_it(db: FakeAsyncDatabase) -> None:
    repo = LearningProfileRepository(db, ObjectId())  # type: ignore[arg-type]

    await repo.upsert(
        answers={"Visual": [1, 2, 3]},
        scores={"visual": 0.8},
        description="A visual learner.",
        questionnaire_version=1,
    )

    profile = await repo.get()
    assert profile is not None
    assert profile["description"] == "A visual learner."
    assert profile["scores"] == {"visual": 0.8}
    assert profile["created_at"] is not None
    assert profile["updated_at"] is not None


async def test_retake_replaces_content_but_keeps_original_created_at(
    db: FakeAsyncDatabase,
) -> None:
    repo = LearningProfileRepository(db, ObjectId())  # type: ignore[arg-type]

    await repo.upsert(
        answers={"Visual": [1]},
        scores={"visual": 0.5},
        description="first",
        questionnaire_version=1,
    )
    first = await repo.get()
    assert first is not None
    original_created_at = first["created_at"]

    await repo.upsert(
        answers={"Auditory": [5]},
        scores={"auditory": 0.9},
        description="retaken",
        questionnaire_version=2,
    )
    second = await repo.get()

    assert second is not None
    assert second["description"] == "retaken"
    assert second["questionnaire_version"] == 2
    assert second["created_at"] == original_created_at  # unchanged across retakes
    assert second["updated_at"] >= first["updated_at"]


async def test_profile_is_owner_scoped(db: FakeAsyncDatabase) -> None:
    owner_a, owner_b = ObjectId(), ObjectId()
    repo_a = LearningProfileRepository(db, owner_a)  # type: ignore[arg-type]
    repo_b = LearningProfileRepository(db, owner_b)  # type: ignore[arg-type]

    await repo_a.upsert(
        answers={}, scores={}, description="owner a's profile", questionnaire_version=1
    )

    assert await repo_b.get() is None
    profile_a = await repo_a.get()
    assert profile_a is not None
    assert profile_a["description"] == "owner a's profile"
