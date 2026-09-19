"""``RedisRateLimiter`` against a mocked Redis client — the same approach
``test_asr_and_tts.py`` uses for the local model adapters: exercise the
real counter logic (TTL set once per window, the over-limit boundary, the
fail-open path) without a running Redis.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from learnai.errors import RateLimited
from learnai.services.limits import RedisRateLimiter, daily_key, window_key


def _redis(*, counts: list[int] | None = None, fails: bool = False) -> MagicMock:
    client = MagicMock()
    if fails:
        client.incr = AsyncMock(side_effect=ConnectionError("redis is down"))
    else:
        client.incr = AsyncMock(side_effect=counts or [1])
    client.expire = AsyncMock()
    return client


async def test_first_hit_sets_the_ttl_once() -> None:
    client = _redis(counts=[1, 2, 3])
    limiter = RedisRateLimiter(client)

    for _ in range(3):
        await limiter.check("k", limit=10, window_seconds=60, description="rate limit")

    assert client.incr.await_count == 3
    # Only the hit that created the key needs the TTL — setting it every
    # time would keep pushing the window's end out under sustained load.
    client.expire.assert_awaited_once_with("k", 60)


async def test_under_the_limit_passes() -> None:
    limiter = RedisRateLimiter(_redis(counts=[5]))

    await limiter.check("k", limit=5, window_seconds=60, description="rate limit")


async def test_over_the_limit_raises_with_retry_after() -> None:
    limiter = RedisRateLimiter(_redis(counts=[6]))

    with pytest.raises(RateLimited) as exc_info:
        await limiter.check("k", limit=5, window_seconds=60, description="rate limit")

    assert "at most 5 per minute" in exc_info.value.message
    assert exc_info.value.detail["retry_after_seconds"] == 60
    assert exc_info.value.status_code == 429


async def test_daily_window_is_labelled_in_days() -> None:
    limiter = RedisRateLimiter(_redis(counts=[101]))

    with pytest.raises(RateLimited, match="at most 100 per day"):
        await limiter.check("k", limit=100, window_seconds=86_400, description="daily quota")


async def test_redis_failure_fails_open() -> None:
    """A Redis outage must not take the API down with it — the limiter is
    a guard against abuse, not a correctness invariant."""
    limiter = RedisRateLimiter(_redis(fails=True))

    await limiter.check("k", limit=1, window_seconds=60, description="rate limit")


def test_window_key_changes_when_the_window_rolls_over() -> None:
    owner = ObjectId()
    now = int(time.time())

    key = window_key("api", owner, window_seconds=60)

    assert str(owner) in key
    assert key.startswith("rl:api:")
    assert key.endswith(str(now // 60))


def test_daily_key_is_utc_day_aligned() -> None:
    owner = ObjectId()

    key = daily_key("generation", owner)

    assert key == f"quota:generation:{owner}:{datetime.now(UTC):%Y-%m-%d}"
