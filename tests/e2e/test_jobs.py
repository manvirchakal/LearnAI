"""Job status polling through the real app — same fake-db/session pattern as
``tests/e2e/test_profile_and_collections.py``. Jobs are only ever created
internally (there's no ``POST``), so tests seed one directly through
``JobRepository`` against the same fake database the app is wired to.
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from learnai.config import Settings, get_settings
from learnai.deps import get_db
from learnai.main import create_app
from learnai.repositories.jobs import JobRepository
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
    fake_db = FakeAsyncDatabase()
    raw_client.app.dependency_overrides[get_db] = lambda: fake_db  # type: ignore[attr-defined]
    raw_client.app.dependency_overrides[get_settings] = lambda: Settings(  # type: ignore[attr-defined]
        session_secret="a-test-secret-at-least-32-bytes-long",
        google_client_id="test-client-id",
    )
    with patch("learnai.routers.auth.verify_google_id_token", return_value=_IDENTITY):
        login = raw_client.post("/auth/google", json={"id_token": "whatever"})
    assert login.status_code == 200

    raw_client.app.state.fake_db = fake_db  # type: ignore[attr-defined]
    raw_client.app.state.owner_id = ObjectId(login.json()["id"])  # type: ignore[attr-defined]

    yield raw_client
    raw_client.app.dependency_overrides.clear()  # type: ignore[attr-defined]


@pytest.fixture
def job_repo(client: TestClient) -> JobRepository:
    return JobRepository(client.app.state.fake_db, client.app.state.owner_id)  # type: ignore[attr-defined]


async def test_get_queued_job(client: TestClient, job_repo: JobRepository) -> None:
    job_id = await job_repo.create(kind="toc_extraction", payload={"material_id": "m1"})

    response = client.get(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(job_id)
    assert body["kind"] == "toc_extraction"
    assert body["status"] == "queued"
    assert body["result"] is None
    assert body["error"] is None


async def test_get_succeeded_job_returns_result(
    client: TestClient, job_repo: JobRepository
) -> None:
    job_id = await job_repo.create(kind="toc_extraction", payload={})
    await job_repo.mark_succeeded(job_id, result={"page_count": 5})

    body = client.get(f"/api/v1/jobs/{job_id}").json()

    assert body["status"] == "succeeded"
    assert body["result"] == {"page_count": 5}


async def test_get_failed_job_returns_error(client: TestClient, job_repo: JobRepository) -> None:
    job_id = await job_repo.create(kind="toc_extraction", payload={})
    await job_repo.mark_failed(job_id, error="boom")

    body = client.get(f"/api/v1/jobs/{job_id}").json()

    assert body["status"] == "failed"
    assert body["error"] == "boom"


def test_get_of_missing_job_is_404(client: TestClient) -> None:
    assert client.get(f"/api/v1/jobs/{ObjectId()}").status_code == 404


def test_get_with_malformed_id_is_422(client: TestClient) -> None:
    assert client.get("/api/v1/jobs/not-an-object-id").status_code == 422


async def test_another_owners_job_is_a_404_not_a_403(
    client: TestClient, raw_client: TestClient, job_repo: JobRepository
) -> None:
    job_id = await job_repo.create(kind="toc_extraction", payload={})

    raw_client.cookies.clear()
    other_identity = GoogleIdentity(
        sub="google-sub-2", email="bob@example.com", name="Bob", picture=None
    )
    with patch("learnai.routers.auth.verify_google_id_token", return_value=other_identity):
        login = raw_client.post("/auth/google", json={"id_token": "whatever"})
    assert login.status_code == 200

    response = raw_client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 404


def test_requires_authentication(client: TestClient) -> None:
    client.cookies.clear()
    assert client.get(f"/api/v1/jobs/{ObjectId()}").status_code == 401
