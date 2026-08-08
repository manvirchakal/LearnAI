"""Job status polling — the ``GET`` half of the ``202 {job_id, poll_url}``
pattern. Jobs themselves are only ever created by other routers (e.g. the
materials upload route enqueuing a TOC extraction); there is no ``POST``
here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter
from pydantic import BaseModel

from learnai.deps import JobRepoDep
from learnai.errors import ValidationError
from learnai.repositories.jobs import JobStatus

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


class JobOut(BaseModel):
    id: str
    kind: str
    status: JobStatus
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime
    updated_at: datetime


def _job_out(doc: dict[str, Any]) -> JobOut:
    return JobOut(
        id=str(doc["_id"]),
        kind=doc["kind"],
        status=doc["status"],
        result=doc["result"],
        error=doc["error"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str, repo: JobRepoDep) -> JobOut:
    try:
        oid = ObjectId(job_id)
    except InvalidId as exc:
        raise ValidationError(f"invalid id: {job_id!r}") from exc
    doc = await repo.get(oid)
    return _job_out(doc)
