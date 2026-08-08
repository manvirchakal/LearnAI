"""Jobs — status tracking for work handed off to the ARQ worker (see
``worker/tasks.py``). A router enqueues a job and returns ``202`` with a
``poll_url``; the client polls ``GET /api/v1/jobs/{id}`` until the status is
terminal. This is what replaces the old ``server/main.py``'s blocking
``time.sleep`` inside request handlers and its open-connection polling loops
that a load balancer's idle timeout would kill mid-job.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from bson import ObjectId

from learnai.errors import NotFound
from learnai.repositories.base import ScopedRepository

JobStatus = Literal["queued", "running", "succeeded", "failed"]


class JobRepository(ScopedRepository[dict[str, Any]]):
    COLLECTION = "jobs"

    async def create(self, *, kind: str, payload: dict[str, Any]) -> ObjectId:
        now = datetime.now(UTC)
        return await self.insert_one(
            {
                "kind": kind,
                "payload": payload,
                "status": "queued",
                "result": None,
                "error": None,
                "created_at": now,
                "updated_at": now,
            }
        )

    async def get(self, job_id: ObjectId) -> dict[str, Any]:
        doc = await self.find_one({"_id": job_id})
        if doc is None:
            raise NotFound(f"job {job_id} not found")
        return doc

    async def mark_running(self, job_id: ObjectId) -> None:
        await self._set_status(job_id, "running")

    async def mark_succeeded(
        self, job_id: ObjectId, *, result: dict[str, Any] | None = None
    ) -> None:
        await self._set_status(job_id, "succeeded", result=result)

    async def mark_failed(self, job_id: ObjectId, *, error: str) -> None:
        await self._set_status(job_id, "failed", error=error)

    async def _set_status(
        self,
        job_id: ObjectId,
        status: JobStatus,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        update: dict[str, Any] = {"status": status, "updated_at": datetime.now(UTC)}
        if result is not None:
            update["result"] = result
        if error is not None:
            update["error"] = error
        result_ = await self.update_one({"_id": job_id}, {"$set": update})
        if result_.matched_count == 0:
            raise NotFound(f"job {job_id} not found")
