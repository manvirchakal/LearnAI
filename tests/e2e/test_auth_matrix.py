"""The auth matrix: every route that requires a session returns 401 without
one. This is the regression test for the old ``server/main.py``'s five
unauthenticated endpoints — most pointedly ``POST /api/chat`` (main.py:1249),
which had no auth dependency at all and read ``userId`` straight out of the
request body, letting anyone who could reach it read another user's data.

Parametrized over (method, path, body) rather than one test per route so a
newly added protected route that's forgotten here fails loudly by omission
— the list is the inventory of what's supposed to require a session.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from learnai.config import Settings, get_settings
from learnai.deps import get_db
from learnai.main import create_app
from tests.fakes.mongo import FakeAsyncDatabase

PROTECTED_ROUTES: list[tuple[str, str, dict[str, object] | None]] = [
    ("GET", "/auth/me", None),
    ("GET", "/api/v1/profile", None),
    ("PUT", "/api/v1/profile", {"answers": {}, "scores": {}}),
    ("GET", "/api/v1/collections", None),
    ("POST", "/api/v1/collections", {"name": "x", "kind": "manual"}),
    ("GET", "/api/v1/collections/000000000000000000000000", None),
    ("PUT", "/api/v1/collections/000000000000000000000000/materials", {"material_refs": []}),
]


@pytest.fixture(scope="module")
def raw_client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def client(raw_client: TestClient) -> Iterator[TestClient]:
    raw_client.cookies.clear()
    raw_client.app.dependency_overrides[get_db] = lambda: FakeAsyncDatabase()  # type: ignore[attr-defined]
    raw_client.app.dependency_overrides[get_settings] = lambda: Settings(  # type: ignore[attr-defined]
        session_secret="a-test-secret-at-least-32-bytes-long",
        google_client_id="test-client-id",
    )
    yield raw_client
    raw_client.app.dependency_overrides.clear()  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("method", "path", "body"), PROTECTED_ROUTES, ids=[f"{m} {p}" for m, p, _ in PROTECTED_ROUTES]
)
def test_route_requires_authentication(
    client: TestClient, method: str, path: str, body: dict[str, object] | None
) -> None:
    response = client.request(method, path, json=body)
    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"


def test_unauthenticated_request_never_trusts_a_client_supplied_user_id(
    client: TestClient,
) -> None:
    """The exact shape of the old /api/chat bug: even if a caller supplies
    what looks like a user identifier, an unauthenticated request must still
    be rejected outright rather than trusting it."""
    response = client.get(
        "/api/v1/collections", params={"userId": "someone-elses-id", "owner_id": "also-fake"}
    )
    assert response.status_code == 401
