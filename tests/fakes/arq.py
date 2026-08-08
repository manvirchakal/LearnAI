"""In-memory ``ArqRedis`` stand-in for tests — records enqueued jobs instead
of talking to a real Redis, so an e2e test can assert what a router
enqueued without a job ever actually running.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeArqPool:
    jobs: list[dict[str, Any]] = field(default_factory=list)

    async def enqueue_job(self, function: str, **kwargs: Any) -> None:
        self.jobs.append({"function": function, "kwargs": kwargs})
