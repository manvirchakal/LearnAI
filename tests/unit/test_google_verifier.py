from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from learnai.errors import Unauthenticated
from learnai.services.auth.google_verifier import verify_google_id_token

_VALID_CLAIMS: dict[str, Any] = {
    "sub": "google-sub-123",
    "email": "ada@example.com",
    "email_verified": True,
    "name": "Ada Lovelace",
    "picture": "https://example.com/pic.jpg",
    "aud": "test-client-id",
}


async def test_valid_token_yields_identity() -> None:
    with patch(
        "learnai.services.auth.google_verifier.google_id_token.verify_oauth2_token",
        return_value=_VALID_CLAIMS,
    ):
        identity = await verify_google_id_token("some-jwt", client_id="test-client-id")

    assert identity.sub == "google-sub-123"
    assert identity.email == "ada@example.com"
    assert identity.name == "Ada Lovelace"
    assert identity.picture == "https://example.com/pic.jpg"


async def test_missing_name_falls_back_to_email() -> None:
    claims = {**_VALID_CLAIMS}
    del claims["name"]
    with patch(
        "learnai.services.auth.google_verifier.google_id_token.verify_oauth2_token",
        return_value=claims,
    ):
        identity = await verify_google_id_token("some-jwt", client_id="test-client-id")

    assert identity.name == "ada@example.com"


async def test_unverified_email_is_rejected() -> None:
    claims = {**_VALID_CLAIMS, "email_verified": False}
    with (
        patch(
            "learnai.services.auth.google_verifier.google_id_token.verify_oauth2_token",
            return_value=claims,
        ),
        pytest.raises(Unauthenticated, match="not verified"),
    ):
        await verify_google_id_token("some-jwt", client_id="test-client-id")


async def test_bad_signature_or_audience_is_rejected() -> None:
    with (
        patch(
            "learnai.services.auth.google_verifier.google_id_token.verify_oauth2_token",
            side_effect=ValueError("Token has wrong audience"),
        ),
        pytest.raises(Unauthenticated, match="invalid Google ID token"),
    ):
        await verify_google_id_token("some-jwt", client_id="test-client-id")
