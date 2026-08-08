"""Auth router, exercised through the real app + FastAPI dependency
injection — only ``get_db``/``get_settings`` are swapped for a fake Mongo
and test settings. ``verify_google_id_token`` is mocked at the router's
import site; real Google verification has its own unit tests in
``tests/unit/test_google_verifier.py``.

Reuses one ``TestClient`` (and pays the lifespan startup cost — a real,
unreachable Mongo connection attempt — exactly once) across the module,
same reasoning as ``tests/e2e/test_health.py``. Each test gets a fresh fake
database and settings via a function-scoped override, and clears cookies
first so no session leaks between tests sharing the one client.
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from learnai.config import Settings, get_settings
from learnai.deps import get_db
from learnai.main import create_app
from learnai.services.auth.google_verifier import GoogleIdentity
from tests.fakes.mongo import FakeAsyncDatabase

_IDENTITY = GoogleIdentity(
    sub="google-sub-1", email="ada@example.com", name="Ada Lovelace", picture=None
)


@pytest.fixture(scope="module")
def raw_client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def client(raw_client: TestClient) -> Iterator[TestClient]:
    raw_client.cookies.clear()
    # One fake database per test, shared across every request that test
    # makes — get_db is re-resolved on each request, so a fresh instance per
    # call (rather than a closed-over one) would silently lose everything
    # written by the previous request in the same test.
    fake_db = FakeAsyncDatabase()
    raw_client.app.dependency_overrides[get_db] = lambda: fake_db  # type: ignore[attr-defined]
    raw_client.app.dependency_overrides[get_settings] = lambda: Settings(  # type: ignore[attr-defined]
        session_secret="a-test-secret-at-least-32-bytes-long",
        google_client_id="test-client-id",
    )
    yield raw_client
    raw_client.app.dependency_overrides.clear()  # type: ignore[attr-defined]


def test_google_login_sets_cookies_and_returns_user(client: TestClient) -> None:
    with patch("learnai.routers.auth.verify_google_id_token", return_value=_IDENTITY):
        response = client.post("/auth/google", json={"id_token": "whatever"})

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "ada@example.com"
    assert body["name"] == "Ada Lovelace"
    assert "learnai_access" in response.cookies
    assert "learnai_refresh" in response.cookies


def test_me_requires_authentication(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401


def test_refresh_without_cookie_is_unauthenticated(client: TestClient) -> None:
    assert client.post("/auth/refresh").status_code == 401


def test_full_login_me_refresh_logout_cycle(client: TestClient) -> None:
    with patch("learnai.routers.auth.verify_google_id_token", return_value=_IDENTITY):
        login = client.post("/auth/google", json={"id_token": "whatever"})
    assert login.status_code == 200

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "ada@example.com"

    old_refresh = client.cookies.get("learnai_refresh")
    refreshed = client.post("/auth/refresh")
    assert refreshed.status_code == 200
    # The refresh token (opaque random bytes) always changes on rotation.
    # The access JWT is not asserted to change here — it has second-
    # granularity iat/exp, so two calls within the same wall-clock second
    # legitimately produce a byte-identical token.
    assert client.cookies.get("learnai_refresh") != old_refresh

    assert client.get("/auth/me").status_code == 200

    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_reused_refresh_token_is_rejected(client: TestClient) -> None:
    """The reuse-detection path, reached through the actual HTTP surface."""
    with patch("learnai.routers.auth.verify_google_id_token", return_value=_IDENTITY):
        client.post("/auth/google", json={"id_token": "whatever"})

    stale_refresh = client.cookies.get("learnai_refresh")
    assert client.post("/auth/refresh").status_code == 200

    client.cookies.set("learnai_refresh", stale_refresh)
    assert client.post("/auth/refresh").status_code == 401


def test_dev_login_disabled_by_default(client: TestClient) -> None:
    assert client.post("/auth/dev-login").status_code == 403


def test_dev_login_when_enabled(client: TestClient) -> None:
    client.app.dependency_overrides[get_settings] = lambda: Settings(  # type: ignore[attr-defined]
        session_secret="a-test-secret-at-least-32-bytes-long",
        google_client_id="test-client-id",
        dev_auth_bypass=True,
    )

    response = client.post("/auth/dev-login")
    assert response.status_code == 200
    assert response.json()["email"] == "dev@localhost"
    assert client.get("/auth/me").status_code == 200
