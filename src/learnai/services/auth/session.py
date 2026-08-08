"""Session issuance: a 15-minute access JWT plus a 30-day rotating refresh
token, backed by ``SessionRepository``.

The access token carries only the user id — never email or other profile
fields, so it can't go stale between mint and expiry; a request handler
looks the user up fresh by id. The refresh token is an opaque random value;
only its SHA-256 hash is ever stored, so a database read alone can't be
replayed as a credential.

Rotation: every refresh redeems the presented token for a new one and
revokes the old one. A ``family_id`` links every token descended from one
login. Presenting an already-revoked token — meaning it was already
redeemed, i.e. stolen and replayed after the legitimate client rotated past
it — revokes the whole family, not just the one token.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from bson import ObjectId

from learnai.errors import Unauthenticated
from learnai.repositories.sessions import SessionRepository

ACCESS_TOKEN_ALGORITHM = "HS256"  # noqa: S105 - an algorithm name, not a credential


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: ObjectId


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    refresh_expires_at: datetime


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class SessionService:
    def __init__(
        self,
        repo: SessionRepository,
        *,
        session_secret: str,
        access_token_ttl_seconds: int,
        refresh_token_ttl_seconds: int,
    ) -> None:
        self._repo = repo
        self._secret = session_secret
        self._access_ttl = timedelta(seconds=access_token_ttl_seconds)
        self._refresh_ttl = timedelta(seconds=refresh_token_ttl_seconds)

    def mint_access_token(self, *, user_id: ObjectId) -> tuple[str, datetime]:
        now = datetime.now(UTC)
        expires_at = now + self._access_ttl
        payload = {"sub": str(user_id), "iat": now, "exp": expires_at}
        token = jwt.encode(payload, self._secret, algorithm=ACCESS_TOKEN_ALGORITHM)
        return token, expires_at

    def verify_access_token(self, token: str) -> AccessTokenClaims:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[ACCESS_TOKEN_ALGORITHM])
        except jwt.PyJWTError as exc:
            raise Unauthenticated(f"invalid access token: {exc}") from exc
        return AccessTokenClaims(user_id=ObjectId(payload["sub"]))

    async def start_session(
        self, *, user_id: ObjectId, user_agent: str | None, ip: str | None
    ) -> IssuedTokens:
        """A fresh login: a new token family."""
        return await self._issue(
            user_id=user_id,
            family_id=secrets.token_urlsafe(16),
            user_agent=user_agent,
            ip=ip,
        )

    async def rotate(
        self, refresh_token: str, *, user_agent: str | None, ip: str | None
    ) -> IssuedTokens:
        """Redeem a refresh token for a new pair, revoking the one presented.

        Raises ``Unauthenticated`` if the token is unrecognized or expired.
        A *revoked* token (already redeemed once) is reuse — the whole
        family is revoked before raising, so every other token descended
        from that login stops working too.
        """
        record = await self._repo.find_by_token_hash(_hash_refresh_token(refresh_token))
        if record is None:
            raise Unauthenticated("refresh token not recognized")

        now = datetime.now(UTC)
        if record["revoked_at"] is not None:
            await self._repo.revoke_family(record["family_id"], revoked_at=now)
            raise Unauthenticated("refresh token reuse detected; session revoked")
        if record["expires_at"] <= now:
            raise Unauthenticated("refresh token expired")

        await self._repo.revoke(record["_id"], revoked_at=now)
        return await self._issue(
            user_id=record["owner_id"],
            family_id=record["family_id"],
            user_agent=user_agent,
            ip=ip,
        )

    async def logout(self, refresh_token: str) -> None:
        """Revoke the presented token's whole family — logout-everywhere for
        this login chain. Silently a no-op for an unrecognized token, since
        the end state (no valid session) is the same either way."""
        record = await self._repo.find_by_token_hash(_hash_refresh_token(refresh_token))
        if record is not None:
            await self._repo.revoke_family(record["family_id"], revoked_at=datetime.now(UTC))

    async def _issue(
        self, *, user_id: ObjectId, family_id: str, user_agent: str | None, ip: str | None
    ) -> IssuedTokens:
        access_token, access_expires_at = self.mint_access_token(user_id=user_id)
        refresh_token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        refresh_expires_at = now + self._refresh_ttl
        await self._repo.create(
            owner_id=user_id,
            token_hash=_hash_refresh_token(refresh_token),
            family_id=family_id,
            user_agent=user_agent,
            ip=ip,
            created_at=now,
            expires_at=refresh_expires_at,
        )
        return IssuedTokens(
            access_token=access_token,
            access_expires_at=access_expires_at,
            refresh_token=refresh_token,
            refresh_expires_at=refresh_expires_at,
        )
