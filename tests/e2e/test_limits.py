"""Rate limits and daily quotas through the real app.

Every other e2e suite runs with limits off (the default), which is what
keeps them from having to think about budgets; this one turns them on and
proves the three things that matter: the request rate caps requests, the
two quotas cap their own kind of work independently of that rate, and one
user exhausting either doesn't affect anyone else.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from learnai.config import LLMTask, Settings, get_settings
from learnai.deps import (
    get_arq_pool,
    get_db,
    get_llm_client,
    get_rate_limiter,
    get_storage,
)
from learnai.main import create_app
from learnai.services.auth.google_verifier import GoogleIdentity
from tests.fakes.arq import FakeArqPool
from tests.fakes.limits import FakeRateLimiter
from tests.fakes.llm import FakeLLMClient
from tests.fakes.mongo import FakeAsyncDatabase
from tests.fakes.storage import FakeStorage

_IDENTITY = GoogleIdentity(
    sub="google-sub-1", email="ada@example.com", name="Ada Lovelace", picture=None
)
_OTHER_IDENTITY = GoogleIdentity(
    sub="google-sub-2", email="bob@example.com", name="Bob", picture=None
)


def _settings(**limits: Any) -> Settings:
    # Generous unless a test dials one down, so a test about one budget
    # never trips a different one first.
    budgets: dict[str, Any] = {
        "rate_limit_per_minute": 100,
        "generation_quota_per_day": 100,
        "ingestion_quota_per_day": 100,
    }
    budgets.update(limits)
    return Settings(
        session_secret="a-test-secret-at-least-32-bytes-long",
        google_client_id="test-client-id",
        rate_limit_enabled=True,
        **budgets,
    )


@pytest.fixture(scope="module")
def raw_client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def client(raw_client: TestClient) -> Iterator[TestClient]:
    raw_client.cookies.clear()
    limiter = FakeRateLimiter()
    # One instance each, closed over — a `lambda: FakeAsyncDatabase()` would
    # hand every request its own empty database, so the user created at
    # login wouldn't exist by the next call.
    fake_db = FakeAsyncDatabase()
    fake_storage = FakeStorage()
    fake_arq = FakeArqPool()
    fake_llm = FakeLLMClient(completions={LLMTask.translation: "Bonjour le monde"})
    overrides: dict[Any, Any] = {
        get_db: lambda: fake_db,
        get_settings: lambda: _settings(),
        get_storage: lambda: fake_storage,
        get_arq_pool: lambda: fake_arq,
        get_rate_limiter: lambda: limiter,
        get_llm_client: lambda: fake_llm,
    }
    raw_client.app.dependency_overrides.update(overrides)  # type: ignore[attr-defined]
    _login(raw_client, _IDENTITY)
    raw_client.app.state.limiter = limiter  # type: ignore[attr-defined]

    yield raw_client
    raw_client.app.dependency_overrides.clear()  # type: ignore[attr-defined]


def _login(client: TestClient, identity: GoogleIdentity) -> None:
    client.cookies.clear()
    with patch("learnai.routers.auth.verify_google_id_token", return_value=identity):
        response = client.post("/auth/google", json={"id_token": "whatever"})
    assert response.status_code == 200


def _set_limits(client: TestClient, **limits: Any) -> None:
    client.app.dependency_overrides[get_settings] = lambda: _settings(**limits)  # type: ignore[attr-defined]


class TestRequestRate:
    def test_over_the_limit_is_429_problem_json_with_retry_after(self, client: TestClient) -> None:
        _set_limits(client, rate_limit_per_minute=2)

        assert client.get("/api/v1/collections").status_code == 200
        assert client.get("/api/v1/collections").status_code == 200
        response = client.get("/api/v1/collections")

        assert response.status_code == 429
        assert response.headers["content-type"] == "application/problem+json"
        assert response.headers["Retry-After"] == "60"
        assert response.json()["title"] == "rate limited"

    def test_the_budget_is_shared_across_routers_not_per_router(self, client: TestClient) -> None:
        """One configured number, one budget per user — otherwise "120 per
        minute" would silently mean 120 per router."""
        _set_limits(client, rate_limit_per_minute=2)

        assert client.get("/api/v1/collections").status_code == 200
        assert client.get("/api/v1/materials").status_code == 200
        assert client.get("/api/v1/materials").status_code == 429

    def test_another_user_has_their_own_budget(
        self, client: TestClient, raw_client: TestClient
    ) -> None:
        _set_limits(client, rate_limit_per_minute=1)
        assert client.get("/api/v1/collections").status_code == 200
        assert client.get("/api/v1/collections").status_code == 429

        _login(raw_client, _OTHER_IDENTITY)

        assert raw_client.get("/api/v1/collections").status_code == 200


class TestQuotas:
    def test_generation_quota_caps_model_spending_endpoints(self, client: TestClient) -> None:
        _set_limits(client, generation_quota_per_day=1)
        body = {"text": "Hello world", "target_language": "fr-FR"}

        assert client.post("/api/v1/media/translate", json=body).status_code == 200
        response = client.post("/api/v1/media/translate", json=body)

        assert response.status_code == 429
        assert "daily generation quota" in response.json()["detail"]
        assert response.headers["Retry-After"] == "86400"

    def test_ingestion_quota_caps_material_creation(self, client: TestClient) -> None:
        _set_limits(client, ingestion_quota_per_day=1)
        body = {"url": "https://youtube.com/watch?v=abc123"}

        assert client.post("/api/v1/media/youtube", json=body).status_code == 202
        response = client.post("/api/v1/media/youtube", json=body)

        assert response.status_code == 429
        assert "daily ingestion quota" in response.json()["detail"]

    def test_the_two_quotas_are_independent(self, client: TestClient) -> None:
        _set_limits(client, generation_quota_per_day=1, ingestion_quota_per_day=1)
        assert (
            client.post(
                "/api/v1/media/translate",
                json={"text": "Hello world", "target_language": "fr-FR"},
            ).status_code
            == 200
        )

        # Exhausting generation must not touch the ingestion budget.
        assert (
            client.post(
                "/api/v1/media/youtube", json={"url": "https://youtube.com/watch?v=abc123"}
            ).status_code
            == 202
        )

    def test_free_endpoints_do_not_consume_a_quota(self, client: TestClient) -> None:
        """Listing collections costs nothing, so it should count against
        the request rate and nothing else."""
        limiter: FakeRateLimiter = client.app.state.limiter  # type: ignore[attr-defined]
        limiter.calls.clear()

        assert client.get("/api/v1/collections").status_code == 200

        assert [call["key"].split(":")[0] for call in limiter.calls] == ["rl"]


def test_limits_are_off_by_default(raw_client: TestClient) -> None:
    """The default Settings leave limiting off so local development and
    the rest of the test suite need no Redis and no budget bookkeeping —
    production turns it on, enforced by the settings validator."""
    limiter = FakeRateLimiter()
    fake_db = FakeAsyncDatabase()
    raw_client.app.dependency_overrides.update(  # type: ignore[attr-defined]
        {
            get_db: lambda: fake_db,
            get_settings: lambda: Settings(
                session_secret="a-test-secret-at-least-32-bytes-long",
                google_client_id="test-client-id",
            ),
            get_rate_limiter: lambda: limiter,
        }
    )
    _login(raw_client, _IDENTITY)

    for _ in range(5):
        assert raw_client.get("/api/v1/collections").status_code == 200

    assert limiter.calls == []
    raw_client.app.dependency_overrides.clear()  # type: ignore[attr-defined]
