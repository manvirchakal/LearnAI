from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from bson import ObjectId

from learnai.errors import Unauthenticated
from learnai.repositories.sessions import SessionRepository
from learnai.services.auth.session import SessionService
from tests.fakes.mongo import FakeAsyncDatabase


@pytest.fixture
def db() -> FakeAsyncDatabase:
    return FakeAsyncDatabase()


@pytest.fixture
def service(db: FakeAsyncDatabase) -> SessionService:
    repo = SessionRepository(db)  # type: ignore[arg-type]
    return SessionService(
        repo,
        session_secret="a-test-secret-at-least-32-bytes-long",
        access_token_ttl_seconds=900,
        refresh_token_ttl_seconds=2_592_000,
    )


async def test_start_session_issues_a_verifiable_access_token(service: SessionService) -> None:
    user_id = ObjectId()

    issued = await service.start_session(user_id=user_id, user_agent="pytest", ip="127.0.0.1")

    claims = service.verify_access_token(issued.access_token)
    assert claims.user_id == user_id


async def test_verify_access_token_rejects_garbage(service: SessionService) -> None:
    with pytest.raises(Unauthenticated):
        service.verify_access_token("not-a-jwt")


async def test_verify_access_token_rejects_expired_token(service: SessionService) -> None:
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": str(ObjectId()),
            "iat": now - timedelta(hours=1),
            "exp": now - timedelta(minutes=1),
        },
        "a-test-secret-at-least-32-bytes-long",
        algorithm="HS256",
    )
    with pytest.raises(Unauthenticated):
        service.verify_access_token(expired)


async def test_verify_access_token_rejects_wrong_secret(service: SessionService) -> None:
    now = datetime.now(UTC)
    forged = jwt.encode(
        {"sub": str(ObjectId()), "iat": now, "exp": now + timedelta(minutes=15)},
        "a-different-secret-entirely-32-bytes+",
        algorithm="HS256",
    )
    with pytest.raises(Unauthenticated):
        service.verify_access_token(forged)


async def test_rotate_issues_a_new_pair_and_invalidates_the_old_refresh_token(
    service: SessionService,
) -> None:
    user_id = ObjectId()
    first = await service.start_session(user_id=user_id, user_agent=None, ip=None)

    second = await service.rotate(first.refresh_token, user_agent=None, ip=None)

    assert service.verify_access_token(second.access_token).user_id == user_id
    assert second.refresh_token != first.refresh_token

    with pytest.raises(Unauthenticated):
        await service.rotate(first.refresh_token, user_agent=None, ip=None)


async def test_rotate_with_unknown_token_raises(service: SessionService) -> None:
    with pytest.raises(Unauthenticated):
        await service.rotate("never-issued", user_agent=None, ip=None)


async def test_reuse_of_a_rotated_away_token_revokes_the_whole_family(
    service: SessionService,
) -> None:
    """The core defense: a stolen refresh token replayed after the
    legitimate client already rotated past it must kill every descendant of
    that login, not just the reused token."""
    user_id = ObjectId()
    first = await service.start_session(user_id=user_id, user_agent=None, ip=None)
    second = await service.rotate(first.refresh_token, user_agent=None, ip=None)

    # Attacker replays the stale (already-rotated) first token.
    with pytest.raises(Unauthenticated):
        await service.rotate(first.refresh_token, user_agent=None, ip=None)

    # The legitimate client's later token is now dead too — the whole family
    # was revoked, not just the reused one.
    with pytest.raises(Unauthenticated):
        await service.rotate(second.refresh_token, user_agent=None, ip=None)


async def test_logout_revokes_the_family(service: SessionService) -> None:
    user_id = ObjectId()
    issued = await service.start_session(user_id=user_id, user_agent=None, ip=None)

    await service.logout(issued.refresh_token)

    with pytest.raises(Unauthenticated):
        await service.rotate(issued.refresh_token, user_agent=None, ip=None)


async def test_logout_of_unknown_token_is_a_silent_no_op(service: SessionService) -> None:
    await service.logout("never-issued")  # must not raise


async def test_rotate_of_an_expired_but_never_reused_token_raises_without_revoking_family(
    service: SessionService, db: FakeAsyncDatabase
) -> None:
    """Natural expiry isn't an attack signal — unlike reuse, it must not
    revoke sibling tokens in the family."""
    user_id = ObjectId()
    issued = await service.start_session(user_id=user_id, user_agent=None, ip=None)

    token_hash = hashlib.sha256(issued.refresh_token.encode("utf-8")).hexdigest()
    record = await db["sessions"].find_one({"token_hash": token_hash})
    assert record is not None
    await db["sessions"].update_one(
        {"_id": record["_id"]}, {"$set": {"expires_at": datetime.now(UTC) - timedelta(seconds=1)}}
    )

    with pytest.raises(Unauthenticated):
        await service.rotate(issued.refresh_token, user_agent=None, ip=None)
