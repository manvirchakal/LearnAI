"""Health endpoints, exercised through the real app factory.

No Mongo/Qdrant/Redis containers here on purpose: this proves the app starts
and degrades gracefully with no backing services reachable, the same
behavior that matters for a container that hasn't finished booting yet.
Phase 1+ integration tests bring up real service containers for the paths
that actually need them.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

from learnai.main import create_app


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as c:
        yield c


def test_liveness_never_touches_a_dependency(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_503_with_no_backing_services(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["checks"] == {"mongo": False, "qdrant": False, "redis": False}


def test_every_response_carries_a_request_id(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.headers["X-Request-ID"]


def test_not_found_route_is_problem_json(client: TestClient) -> None:
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["status"] == 404
    assert body["request_id"]
