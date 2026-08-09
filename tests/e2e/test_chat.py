"""Chat router, exercised through the real app — same fake-db/storage/
extraction pattern as ``tests/e2e/test_generation.py``, plus a
``FakeLLMClient`` scripted with an agent response so nothing here calls a
real Anthropic endpoint.
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

from learnai.config import LLMTask, Settings, get_settings
from learnai.deps import (
    get_arq_pool,
    get_db,
    get_embedder,
    get_extractor,
    get_llm_client,
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
from tests.fakes.llm import FakeLLMClient
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
    fake_llm = FakeLLMClient(agent_responses={LLMTask.chat: "The chain rule multiplies..."})

    overrides: dict[Any, Any] = {
        get_db: lambda: fake_db,
        get_settings: lambda: Settings(
            session_secret="a-test-secret-at-least-32-bytes-long",
            google_client_id="test-client-id",
        ),
        get_storage: lambda: fake_storage,
        get_extractor: lambda: fake_extractor,
        get_arq_pool: lambda: FakeArqPool(),
        get_embedder: lambda: FakeEmbedder(),
        get_vector_store: lambda: FakeVectorStore(),
        get_llm_client: lambda: fake_llm,
    }
    raw_client.app.dependency_overrides.update(overrides)  # type: ignore[attr-defined]

    with patch("learnai.routers.auth.verify_google_id_token", return_value=_IDENTITY):
        login = raw_client.post("/auth/google", json={"id_token": "whatever"})
    assert login.status_code == 200

    raw_client.app.state.fake_db = fake_db  # type: ignore[attr-defined]
    raw_client.app.state.fake_storage = fake_storage  # type: ignore[attr-defined]
    raw_client.app.state.fake_extractor = fake_extractor  # type: ignore[attr-defined]
    raw_client.app.state.fake_llm = fake_llm  # type: ignore[attr-defined]
    raw_client.app.state.owner_id = ObjectId(login.json()["id"])  # type: ignore[attr-defined]

    yield raw_client
    raw_client.app.dependency_overrides.clear()  # type: ignore[attr-defined]


async def _ready_collection(client: TestClient) -> str:
    fake_extractor: FakeExtractor = client.app.state.fake_extractor  # type: ignore[attr-defined]
    fake_extractor.toc_result = TOCResult(
        tree=[TreeNode(node_id="1", title="Chapter 1", start_page=1, end_page=5)],
        confidence="high",
    )
    fake_extractor.section_results["1"] = SectionContent(
        node_id="1", text="The chain rule multiplies derivatives."
    )

    upload: httpx.Response = client.post(
        "/api/v1/materials", files={"file": ("calculus.pdf", _make_pdf(5), "application/pdf")}
    )
    body = upload.json()

    ctx = {
        "db": client.app.state.fake_db,  # type: ignore[attr-defined]
        "storage": client.app.state.fake_storage,  # type: ignore[attr-defined]
        "extractor": fake_extractor,
    }
    owner_id = client.app.state.owner_id  # type: ignore[attr-defined]
    await extract_toc_task(
        ctx, owner_id=str(owner_id), material_id=body["material_id"], job_id=body["job_id"]
    )

    collection = client.post(
        "/api/v1/collections", json={"name": "Calculus", "kind": "manual"}
    ).json()
    put_response = client.put(
        f"/api/v1/collections/{collection['id']}/materials",
        json={"material_refs": [{"material_id": body["material_id"], "section_ids": ["1"]}]},
    )
    assert put_response.status_code == 200
    return str(collection["id"])


class TestChat:
    async def test_history_starts_empty(self, client: TestClient) -> None:
        collection_id = await _ready_collection(client)

        response = client.get(f"/api/v1/collections/{collection_id}/chat")

        assert response.status_code == 200
        assert response.json() == []

    async def test_send_message_returns_assistant_reply(self, client: TestClient) -> None:
        collection_id = await _ready_collection(client)

        response = client.post(
            f"/api/v1/collections/{collection_id}/chat",
            json={"message": "What's the chain rule?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["role"] == "assistant"
        assert body["content"] == "The chain rule multiplies..."
        assert body["citations"] == []

    async def test_history_accumulates_across_messages(self, client: TestClient) -> None:
        collection_id = await _ready_collection(client)

        client.post(f"/api/v1/collections/{collection_id}/chat", json={"message": "First question"})
        client.post(
            f"/api/v1/collections/{collection_id}/chat", json={"message": "Second question"}
        )

        history = client.get(f"/api/v1/collections/{collection_id}/chat").json()

        assert [m["role"] for m in history] == ["user", "assistant", "user", "assistant"]
        assert [m["seq"] for m in history] == [1, 2, 3, 4]
        assert history[0]["content"] == "First question"
        assert history[2]["content"] == "Second question"

    async def test_empty_message_is_422(self, client: TestClient) -> None:
        collection_id = await _ready_collection(client)

        response = client.post(f"/api/v1/collections/{collection_id}/chat", json={"message": ""})

        assert response.status_code == 422

    async def test_missing_collection_is_404(self, client: TestClient) -> None:
        assert client.get(f"/api/v1/collections/{ObjectId()}/chat").status_code == 404
        response = client.post(f"/api/v1/collections/{ObjectId()}/chat", json={"message": "hi"})
        assert response.status_code == 404


class TestTenantIsolation:
    async def test_another_owners_collection_is_a_404_not_a_403(
        self, client: TestClient, raw_client: TestClient
    ) -> None:
        collection_id = await _ready_collection(client)

        raw_client.cookies.clear()
        other_identity = GoogleIdentity(
            sub="google-sub-2", email="bob@example.com", name="Bob", picture=None
        )
        with patch("learnai.routers.auth.verify_google_id_token", return_value=other_identity):
            login = raw_client.post("/auth/google", json={"id_token": "whatever"})
        assert login.status_code == 200

        assert raw_client.get(f"/api/v1/collections/{collection_id}/chat").status_code == 404
        assert (
            raw_client.post(
                f"/api/v1/collections/{collection_id}/chat", json={"message": "hi"}
            ).status_code
            == 404
        )
