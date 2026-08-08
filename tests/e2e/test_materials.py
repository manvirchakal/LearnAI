"""Materials/sections routers, exercised through the real app — same
fake-db/settings-override pattern as ``tests/e2e/test_profile_and_collections.py``,
plus fakes for storage, extraction, and the ARQ pool so nothing here talks
to a real filesystem, Anthropic, or Redis.

The worker itself (``worker/tasks.extract_toc_task``) is unit-tested
against fakes in ``tests/unit/test_worker_tasks.py`` and is never running
in this process — tests that need a material past ``uploaded`` invoke it
directly here, standing in for what the real worker would do after
draining the (faked) queue.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import patch

import httpx
import pymupdf
import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from learnai.config import Settings, get_settings
from learnai.deps import (
    get_arq_pool,
    get_db,
    get_embedder,
    get_extractor,
    get_storage,
    get_vector_store,
)
from learnai.main import create_app
from learnai.schemas.documents import SectionContent, TOCResult, TreeNode
from learnai.services.auth.google_verifier import GoogleIdentity
from learnai.worker.tasks import extract_toc_task
from tests.fakes.arq import FakeArqPool
from tests.fakes.embedder import FakeEmbedder
from tests.fakes.extraction import FakeExtractor
from tests.fakes.mongo import FakeAsyncDatabase
from tests.fakes.storage import FakeStorage
from tests.fakes.vector_store import FakeVectorStore

_IDENTITY = GoogleIdentity(
    sub="google-sub-1", email="ada@example.com", name="Ada Lovelace", picture=None
)


def _make_pdf(num_pages: int) -> bytes:
    doc = pymupdf.open()  # type: ignore[no-untyped-call]
    for _ in range(num_pages):
        doc.new_page()
    buffer: bytes = doc.tobytes()  # type: ignore[no-untyped-call]
    doc.close()  # type: ignore[no-untyped-call]
    return buffer


@pytest.fixture(scope="module")
def raw_client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def client(raw_client: TestClient) -> Iterator[TestClient]:
    raw_client.cookies.clear()
    fake_db = FakeAsyncDatabase()
    fake_storage = FakeStorage()
    fake_extractor = FakeExtractor()
    fake_arq = FakeArqPool()
    fake_embedder = FakeEmbedder()
    fake_vector_store = FakeVectorStore()

    overrides: dict[Any, Any] = {
        get_db: lambda: fake_db,
        get_settings: lambda: Settings(
            session_secret="a-test-secret-at-least-32-bytes-long",
            google_client_id="test-client-id",
        ),
        get_storage: lambda: fake_storage,
        get_extractor: lambda: fake_extractor,
        get_arq_pool: lambda: fake_arq,
        get_embedder: lambda: fake_embedder,
        get_vector_store: lambda: fake_vector_store,
    }
    raw_client.app.dependency_overrides.update(overrides)  # type: ignore[attr-defined]

    with patch("learnai.routers.auth.verify_google_id_token", return_value=_IDENTITY):
        login = raw_client.post("/auth/google", json={"id_token": "whatever"})
    assert login.status_code == 200

    raw_client.app.state.fake_db = fake_db  # type: ignore[attr-defined]
    raw_client.app.state.fake_storage = fake_storage  # type: ignore[attr-defined]
    raw_client.app.state.fake_extractor = fake_extractor  # type: ignore[attr-defined]
    raw_client.app.state.fake_arq = fake_arq  # type: ignore[attr-defined]
    raw_client.app.state.fake_embedder = fake_embedder  # type: ignore[attr-defined]
    raw_client.app.state.fake_vector_store = fake_vector_store  # type: ignore[attr-defined]
    raw_client.app.state.owner_id = ObjectId(login.json()["id"])  # type: ignore[attr-defined]

    yield raw_client
    raw_client.app.dependency_overrides.clear()  # type: ignore[attr-defined]


def _upload(
    client: TestClient, *, num_pages: int = 5, content_type: str = "application/pdf"
) -> httpx.Response:
    response: httpx.Response = client.post(
        "/api/v1/materials",
        files={"file": ("calculus.pdf", _make_pdf(num_pages), content_type)},
    )
    return response


async def _run_toc_job(client: TestClient, material_id: str, job_id: str) -> None:
    """Stands in for the worker draining the (faked) queue."""
    ctx = {
        "db": client.app.state.fake_db,  # type: ignore[attr-defined]
        "storage": client.app.state.fake_storage,  # type: ignore[attr-defined]
        "extractor": client.app.state.fake_extractor,  # type: ignore[attr-defined]
    }
    owner_id = client.app.state.owner_id  # type: ignore[attr-defined]
    await extract_toc_task(ctx, owner_id=str(owner_id), material_id=material_id, job_id=job_id)


class TestUpload:
    def test_upload_returns_202_with_poll_url(self, client: TestClient) -> None:
        response = _upload(client)

        assert response.status_code == 202
        body = response.json()
        assert body["poll_url"] == f"/api/v1/jobs/{body['job_id']}"

        material = client.get(f"/api/v1/materials/{body['material_id']}").json()
        assert material["status"] == "uploaded"
        assert material["filename"] == "calculus.pdf"

        job = client.get(body["poll_url"]).json()
        assert job["status"] == "queued"

        fake_arq: FakeArqPool = client.app.state.fake_arq  # type: ignore[attr-defined]
        assert fake_arq.jobs == [
            {
                "function": "extract_toc_task",
                "kwargs": {
                    "owner_id": str(client.app.state.owner_id),  # type: ignore[attr-defined]
                    "material_id": body["material_id"],
                    "job_id": body["job_id"],
                },
            }
        ]

    def test_upload_rejects_non_pdf_content_type(self, client: TestClient) -> None:
        response = _upload(client, content_type="text/plain")
        assert response.status_code == 422

    def test_upload_rejects_empty_file(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/materials", files={"file": ("empty.pdf", b"", "application/pdf")}
        )
        assert response.status_code == 422

    def test_upload_requires_authentication(self, client: TestClient) -> None:
        client.cookies.clear()
        assert _upload(client).status_code == 401


class TestList:
    def test_list_is_owner_scoped(self, client: TestClient, raw_client: TestClient) -> None:
        # `client` and `raw_client` are the same TestClient — capture owner
        # A's view before switching identity below, which replaces its
        # session cookie in place.
        _upload(client)
        assert len(client.get("/api/v1/materials").json()) == 1

        raw_client.cookies.clear()
        other_identity = GoogleIdentity(
            sub="google-sub-2", email="bob@example.com", name="Bob", picture=None
        )
        with patch("learnai.routers.auth.verify_google_id_token", return_value=other_identity):
            login = raw_client.post("/auth/google", json={"id_token": "whatever"})
        assert login.status_code == 200

        assert raw_client.get("/api/v1/materials").json() == []


class TestTree:
    async def test_tree_before_ready_is_409(self, client: TestClient) -> None:
        body = _upload(client).json()

        response = client.get(f"/api/v1/materials/{body['material_id']}/tree")
        assert response.status_code == 409

    async def test_tree_after_toc_extraction(self, client: TestClient) -> None:
        fake_extractor: FakeExtractor = client.app.state.fake_extractor  # type: ignore[attr-defined]
        fake_extractor.toc_result = TOCResult(
            tree=[TreeNode(node_id="1", title="Chapter 1", start_page=1, end_page=5)],
            confidence="high",
        )
        body = _upload(client).json()
        await _run_toc_job(client, body["material_id"], body["job_id"])

        material = client.get(f"/api/v1/materials/{body['material_id']}").json()
        assert material["status"] == "toc_ready"
        assert material["page_count"] == 5

        tree = client.get(f"/api/v1/materials/{body['material_id']}/tree").json()
        assert tree["tree"][0]["title"] == "Chapter 1"

    def test_tree_of_missing_material_is_404(self, client: TestClient) -> None:
        assert client.get(f"/api/v1/materials/{ObjectId()}/tree").status_code == 404

    def test_get_with_malformed_id_is_422(self, client: TestClient) -> None:
        assert client.get("/api/v1/materials/not-an-object-id").status_code == 422


class TestSections:
    async def test_first_read_extracts_then_caches(self, client: TestClient) -> None:
        fake_extractor: FakeExtractor = client.app.state.fake_extractor  # type: ignore[attr-defined]
        fake_extractor.toc_result = TOCResult(
            tree=[TreeNode(node_id="1", title="Chapter 1", start_page=1, end_page=5)],
            confidence="high",
        )
        fake_extractor.section_results["1"] = SectionContent(
            node_id="1", text="The limit of a function...", citations=[]
        )
        body = _upload(client).json()
        await _run_toc_job(client, body["material_id"], body["job_id"])

        first = client.get(f"/api/v1/materials/{body['material_id']}/sections/1")
        assert first.status_code == 200
        assert first.json()["text"] == "The limit of a function..."
        extract_calls = [c for c in fake_extractor.calls if c["op"] == "extract_section"]
        assert len(extract_calls) == 1

        second = client.get(f"/api/v1/materials/{body['material_id']}/sections/1")
        assert second.status_code == 200
        assert second.json()["text"] == "The limit of a function..."
        # Cached — no second extraction call.
        extract_calls = [c for c in fake_extractor.calls if c["op"] == "extract_section"]
        assert len(extract_calls) == 1

        fake_vector_store: FakeVectorStore = client.app.state.fake_vector_store  # type: ignore[attr-defined]
        assert len(fake_vector_store.points) == 1
        (point,) = fake_vector_store.points.values()
        assert point.text == "The limit of a function..."

    async def test_unknown_node_id_is_404(self, client: TestClient) -> None:
        fake_extractor: FakeExtractor = client.app.state.fake_extractor  # type: ignore[attr-defined]
        fake_extractor.toc_result = TOCResult(
            tree=[TreeNode(node_id="1", title="Chapter 1", start_page=1, end_page=5)],
            confidence="high",
        )
        body = _upload(client).json()
        await _run_toc_job(client, body["material_id"], body["job_id"])

        response = client.get(f"/api/v1/materials/{body['material_id']}/sections/99")
        assert response.status_code == 404

    def test_section_before_ready_is_409(self, client: TestClient) -> None:
        body = _upload(client).json()
        response = client.get(f"/api/v1/materials/{body['material_id']}/sections/1")
        assert response.status_code == 409


class TestTenantIsolation:
    async def test_another_owners_material_is_a_404_not_a_403(
        self, client: TestClient, raw_client: TestClient
    ) -> None:
        body = _upload(client).json()

        raw_client.cookies.clear()
        other_identity = GoogleIdentity(
            sub="google-sub-2", email="bob@example.com", name="Bob", picture=None
        )
        with patch("learnai.routers.auth.verify_google_id_token", return_value=other_identity):
            login = raw_client.post("/auth/google", json={"id_token": "whatever"})
        assert login.status_code == 200

        assert raw_client.get(f"/api/v1/materials/{body['material_id']}").status_code == 404
        assert raw_client.get(f"/api/v1/materials/{body['material_id']}/tree").status_code == 404
        assert (
            raw_client.get(f"/api/v1/materials/{body['material_id']}/sections/1").status_code == 404
        )
