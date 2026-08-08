from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from bson import ObjectId

from learnai.repositories.sessions import SessionRepository
from learnai.repositories.users import UserRepository
from tests.fakes.mongo import FakeAsyncDatabase


@pytest.fixture
def db() -> FakeAsyncDatabase:
    return FakeAsyncDatabase()


class TestUserRepository:
    async def test_first_login_creates_a_user(self, db: FakeAsyncDatabase) -> None:
        repo = UserRepository(db)  # type: ignore[arg-type]

        user = await repo.upsert_from_google(
            google_sub="sub-1", email="a@example.com", email_verified=True, name="Ada", picture=None
        )

        assert user["google_sub"] == "sub-1"
        assert user["email"] == "a@example.com"
        assert user["created_at"] is not None
        assert user["last_login_at"] is not None

    async def test_second_login_updates_profile_but_keeps_created_at(
        self, db: FakeAsyncDatabase
    ) -> None:
        repo = UserRepository(db)  # type: ignore[arg-type]

        first = await repo.upsert_from_google(
            google_sub="sub-1", email="a@example.com", email_verified=True, name="Ada", picture=None
        )
        second = await repo.upsert_from_google(
            google_sub="sub-1",
            email="a@example.com",
            email_verified=True,
            name="Ada Lovelace",  # display name changed on Google's side
            picture="https://example.com/pic.jpg",
        )

        assert second["name"] == "Ada Lovelace"
        assert second["picture"] == "https://example.com/pic.jpg"
        assert second["created_at"] == first["created_at"]
        # Same document updated in place, not a second one inserted.
        assert second["_id"] == first["_id"]

    async def test_find_by_google_sub_returns_none_when_unknown(
        self, db: FakeAsyncDatabase
    ) -> None:
        repo = UserRepository(db)  # type: ignore[arg-type]
        assert await repo.find_by_google_sub("never-registered") is None

    async def test_find_by_id_roundtrips(self, db: FakeAsyncDatabase) -> None:
        repo = UserRepository(db)  # type: ignore[arg-type]
        created = await repo.upsert_from_google(
            google_sub="sub-1", email="a@example.com", email_verified=True, name="Ada", picture=None
        )
        found = await repo.find_by_id(created["_id"])
        assert found is not None
        assert found["google_sub"] == "sub-1"


class TestSessionRepository:
    async def test_create_then_find_by_token_hash(self, db: FakeAsyncDatabase) -> None:
        repo = SessionRepository(db)  # type: ignore[arg-type]
        owner = ObjectId()
        now = datetime.now(UTC)

        session_id = await repo.create(
            owner_id=owner,
            token_hash="hash-1",
            family_id="family-1",
            user_agent="pytest",
            ip="127.0.0.1",
            created_at=now,
            expires_at=now + timedelta(days=30),
        )

        found = await repo.find_by_token_hash("hash-1")
        assert found is not None
        assert found["_id"] == session_id
        assert found["owner_id"] == owner
        assert found["revoked_at"] is None

    async def test_revoke_marks_only_that_session(self, db: FakeAsyncDatabase) -> None:
        repo = SessionRepository(db)  # type: ignore[arg-type]
        owner = ObjectId()
        now = datetime.now(UTC)

        id_a = await repo.create(
            owner_id=owner,
            token_hash="hash-a",
            family_id="family-1",
            user_agent=None,
            ip=None,
            created_at=now,
            expires_at=now + timedelta(days=30),
        )
        await repo.create(
            owner_id=owner,
            token_hash="hash-b",
            family_id="family-2",
            user_agent=None,
            ip=None,
            created_at=now,
            expires_at=now + timedelta(days=30),
        )

        await repo.revoke(id_a, revoked_at=now)

        a = await repo.find_by_token_hash("hash-a")
        b = await repo.find_by_token_hash("hash-b")
        assert a is not None
        assert a["revoked_at"] == now
        assert b is not None
        assert b["revoked_at"] is None

    async def test_revoke_family_revokes_every_token_in_the_chain(
        self, db: FakeAsyncDatabase
    ) -> None:
        """The reuse-detection scenario: a stolen refresh token gets replayed
        after the legitimate client already rotated past it. Revoking the
        family kills every descendant, not just the one presented."""
        repo = SessionRepository(db)  # type: ignore[arg-type]
        owner = ObjectId()
        now = datetime.now(UTC)

        for i in range(3):  # simulates 3 rotations of the same family
            await repo.create(
                owner_id=owner,
                token_hash=f"hash-{i}",
                family_id="family-1",
                user_agent=None,
                ip=None,
                created_at=now,
                expires_at=now + timedelta(days=30),
            )
        other_family_id = await repo.create(
            owner_id=owner,
            token_hash="unrelated-hash",
            family_id="family-2",
            user_agent=None,
            ip=None,
            created_at=now,
            expires_at=now + timedelta(days=30),
        )

        await repo.revoke_family("family-1", revoked_at=now)

        for i in range(3):
            doc = await repo.find_by_token_hash(f"hash-{i}")
            assert doc is not None
            assert doc["revoked_at"] == now

        unrelated = await repo.find_by_token_hash("unrelated-hash")
        assert unrelated is not None
        assert unrelated["revoked_at"] is None
        assert unrelated["_id"] == other_family_id
