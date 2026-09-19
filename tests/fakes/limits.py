"""In-memory ``RateLimiter`` stand-in for tests — a real fixed-window
counter, just backed by a dict instead of Redis, so an e2e test can
actually exhaust a limit and see the 429 rather than only asserting that
a check was attempted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from learnai.errors import RateLimited


@dataclass
class FakeRateLimiter:
    counts: dict[str, int] = field(default_factory=dict)
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def check(self, key: str, *, limit: int, window_seconds: int, description: str) -> None:
        self.calls.append({"key": key, "limit": limit, "window_seconds": window_seconds})
        self.counts[key] = self.counts.get(key, 0) + 1
        if self.counts[key] > limit:
            raise RateLimited(
                f"{description} exceeded: at most {limit} per window",
                detail={"retry_after_seconds": window_seconds},
            )
