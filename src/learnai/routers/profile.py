"""Learning-profile API: submit/retrieve the questionnaire result.

One document per user (see ``LearningProfileRepository`` — an upsert
against a unique ``owner_id`` index). ``description`` is client-supplied for
now; Phase 2 replaces it with an LLM-generated one over the same schema,
without touching this router's shape.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from learnai.deps import LearningProfileRepoDep

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


class ProfileSubmission(BaseModel):
    answers: dict[str, list[int]]
    scores: dict[str, float]
    description: str
    questionnaire_version: int = 1


class ProfileOut(BaseModel):
    answers: dict[str, list[int]]
    scores: dict[str, float]
    description: str
    questionnaire_version: int
    created_at: datetime
    updated_at: datetime


def _profile_out(doc: dict[str, Any]) -> ProfileOut:
    return ProfileOut(
        answers=doc["answers"],
        scores=doc["scores"],
        description=doc["description"],
        questionnaire_version=doc["questionnaire_version"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.get("", response_model=ProfileOut | None)
async def get_profile(repo: LearningProfileRepoDep) -> ProfileOut | None:
    doc = await repo.get()
    return _profile_out(doc) if doc is not None else None


@router.put("", response_model=ProfileOut)
async def submit_profile(body: ProfileSubmission, repo: LearningProfileRepoDep) -> ProfileOut:
    await repo.upsert(
        answers=body.answers,
        scores=body.scores,
        description=body.description,
        questionnaire_version=body.questionnaire_version,
    )
    doc = await repo.get()
    if doc is None:  # pragma: no cover - unreachable: upsert() above just wrote it
        raise RuntimeError("learning profile disappeared immediately after upsert")
    return _profile_out(doc)
