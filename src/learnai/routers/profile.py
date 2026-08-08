"""Learning-profile API: submit/retrieve the questionnaire result.

One document per user (see ``LearningProfileRepository`` — an upsert
against a unique ``owner_id`` index). ``description`` is generated
server-side by the configured LLM backend from the submitted scores —
never client-supplied, so it can't be spoofed and stays consistent
regardless of which frontend build submitted the questionnaire.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from learnai.config import LLMTask
from learnai.deps import LearningProfileRepoDep, LLMClientDep
from learnai.services.llm.prompts import render

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


class ProfileSubmission(BaseModel):
    answers: dict[str, list[int]]
    scores: dict[str, float]
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
async def submit_profile(
    body: ProfileSubmission, repo: LearningProfileRepoDep, llm: LLMClientDep
) -> ProfileOut:
    description = await llm.complete(
        task=LLMTask.profile_description,
        prompt=render("profile_description.j2", scores=body.scores),
    )
    await repo.upsert(
        answers=body.answers,
        scores=body.scores,
        description=description,
        questionnaire_version=body.questionnaire_version,
    )
    doc = await repo.get()
    if doc is None:  # pragma: no cover - unreachable: upsert() above just wrote it
        raise RuntimeError("learning profile disappeared immediately after upsert")
    return _profile_out(doc)
