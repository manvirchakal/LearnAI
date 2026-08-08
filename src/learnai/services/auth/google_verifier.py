"""Google ID token verification.

Replaces the old hand-rolled JWKS fetch + ``jose`` verification (and its
import-time network call at the old ``main.py:154``) with ``google-auth``'s
``id_token.verify_oauth2_token``, which fetches and caches Google's signing
certs itself, lazily, on first use.

A verified Google ID token proves who signed in *once*; it is not our
session. ``services/auth/session.py`` mints what we actually keep — a short
access JWT plus a rotating refresh token — after this succeeds.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from learnai.errors import Unauthenticated

# google-auth caches fetched certs on this instance across calls; building it
# once and reusing it is deliberate (not import-time I/O — construction here
# does no network access, only lazy fetches on first verify).
_request = google_requests.Request()


@dataclass(frozen=True, slots=True)
class GoogleIdentity:
    sub: str
    email: str
    name: str
    picture: str | None


async def verify_google_id_token(token: str, *, client_id: str) -> GoogleIdentity:
    """Verify signature, issuer, audience, and expiry.

    Raises ``Unauthenticated`` for anything wrong with the token — bad
    signature, wrong audience, expired, unverified email. The verification
    call itself is blocking (it may do a synchronous HTTPS fetch on a cache
    miss), so it runs off the event loop via ``asyncio.to_thread``.
    """
    try:
        claims = await asyncio.to_thread(
            google_id_token.verify_oauth2_token, token, _request, client_id
        )
    except ValueError as exc:
        raise Unauthenticated(f"invalid Google ID token: {exc}") from exc

    if not claims.get("email_verified", False):
        raise Unauthenticated("Google account email is not verified")

    return GoogleIdentity(
        sub=claims["sub"],
        email=claims["email"],
        name=claims.get("name", claims["email"]),
        picture=claims.get("picture"),
    )
