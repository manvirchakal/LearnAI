"""Rate limits and daily quotas — one mechanism, two policies.

A quota is just a limit over a longer, day-aligned window, so both go
through the same fixed-window counter rather than two parallel
implementations. Call sites differ only in the key they build and the
numbers they pass (see ``deps.py``'s ``rate_limit``/``daily_quota``).

Fixed-window deliberately, rather than a sliding log or token bucket:
it's one ``INCR`` plus one ``EXPIRE`` against a key Redis cleans up
itself, with no per-request scanning or clock arithmetic. Its known
weakness — up to 2x the limit across a window boundary — doesn't matter
for the job here, which is bounding runaway cost and abuse, not metering
to the individual request.

**Fails open.** A Redis outage must not take the API down with it: this
is a guard against abuse, not a correctness invariant, so a failed check
is logged and allowed through — the same reasoning
``get_or_extract_section`` uses for treating a failed index write as
non-fatal to the read it was piggybacking on.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Protocol

from bson import ObjectId
from redis.asyncio import Redis

from learnai.errors import RateLimited
from learnai.logging import get_logger

logger = get_logger(__name__)


class RateLimiter(Protocol):
    async def check(
        self, key: str, *, limit: int, window_seconds: int, description: str
    ) -> None: ...


def window_key(scope: str, owner_id: ObjectId, *, window_seconds: int) -> str:
    """Key for a short rolling limit. The window index is part of the key,
    so a new window starts with a fresh counter rather than needing the
    old one reset."""
    bucket = int(time.time()) // window_seconds
    return f"rl:{scope}:{owner_id}:{bucket}"


def daily_key(scope: str, owner_id: ObjectId) -> str:
    """Key for a daily quota. Day-aligned in UTC so the reset is a fixed,
    explainable time rather than 24h after whenever the user first hit it."""
    return f"quota:{scope}:{owner_id}:{datetime.now(UTC):%Y-%m-%d}"


class RedisRateLimiter:
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def check(self, key: str, *, limit: int, window_seconds: int, description: str) -> None:
        try:
            count = int(await self._client.incr(key))
            if count == 1:
                # Only the first hit in a window needs the TTL; setting it
                # on every hit would turn a fixed window into a sliding one
                # that never expires under sustained traffic.
                await self._client.expire(key, window_seconds)
        except Exception:
            # Fails open — see the module docstring.
            logger.error("rate_limit_check_failed", key=key, exc_info=True)
            return

        if count > limit:
            raise RateLimited(
                f"{description} exceeded: at most {limit} per {_window_label(window_seconds)}",
                detail={"retry_after_seconds": window_seconds},
            )


def _window_label(window_seconds: int) -> str:
    if window_seconds % 86_400 == 0:
        days = window_seconds // 86_400
        return "day" if days == 1 else f"{days} days"
    if window_seconds % 60 == 0:
        minutes = window_seconds // 60
        return "minute" if minutes == 1 else f"{minutes} minutes"
    return f"{window_seconds} seconds"
