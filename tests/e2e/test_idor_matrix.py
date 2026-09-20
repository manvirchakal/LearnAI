"""The IDOR matrix: every ``{id}`` route, probed with another user's id.

Individual suites already check tenant isolation for the resources they
own; this is the inventory in one place, so a newly added ``{id}`` route
that forgets owner scoping fails here by omission rather than being
noticed only if someone remembers to write the isolation test alongside
it.

Every probe must answer **404, never 403** — a 403 would confirm the
resource exists, which is an existence oracle. That's the guarantee
``ScopedRepository`` is built to give (see its module docstring): a
missing document and someone else's document are indistinguishable.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import patch

import pymupdf
import pytest
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
from learnai.services.auth.google_verifier import GoogleIdentity
from tests.fakes.arq import FakeArqPool
from tests.fakes.embedder import FakeEmbedder
from tests.fakes.extraction import FakeExtractor
from tests.fakes.llm import FakeLLMClient
from tests.fakes.mongo import FakeAsyncDatabase
from tests.fakes.storage import FakeStorage
from tests.fakes.vector_store import FakeVectorStore

_OWNER = GoogleIdentity(
    sub="google-sub-owner", email="ada@example.com", name="Ada Lovelace", picture=None
)
_INTRUDER = GoogleIdentity(
    sub="google-sub-intruder", email="mallory@example.com", name="Mallory", picture=None
)


def _make_pdf() -> bytes:
    doc = pymupdf.open()  # type: ignore[no-untyped-call]
    doc.new_page()
    buffer: bytes = doc.tobytes()  # type: ignore[no-untyped-call]
    doc.close()  # type: ignore[no-untyped-call]
    return buffer


@pytest.fixture(scope="module")
def raw_client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c


def _login(client: TestClient, identity: GoogleIdentity) -> None:
    client.cookies.clear()
    with patch("learnai.routers.auth.verify_google_id_token", return_value=identity):
        response = client.post("/auth/google", json={"id_token": "whatever"})
    assert response.status_code == 200


@pytest.fixture
def owned_ids(raw_client: TestClient) -> Iterator[dict[str, str]]:
    """Resources that genuinely belong to the owner, with the client left
    logged in as the intruder."""
    fake_db = FakeAsyncDatabase()
    fake_storage = FakeStorage()
    fake_extractor = FakeExtractor()
    fake_arq = FakeArqPool()
    overrides: dict[Any, Any] = {
        get_db: lambda: fake_db,
        get_settings: lambda: Settings(
            session_secret="a-test-secret-at-least-32-bytes-long",
            google_client_id="test-client-id",
        ),
        get_storage: lambda: fake_storage,
        get_extractor: lambda: fake_extractor,
        get_arq_pool: lambda: fake_arq,
        get_embedder: lambda: FakeEmbedder(),
        get_vector_store: lambda: FakeVectorStore(),
        get_llm_client: lambda: FakeLLMClient(
            completions={LLMTask.translation: "Bonjour"},
            agent_responses={LLMTask.chat: "hello"},
        ),
    }
    raw_client.app.dependency_overrides.update(overrides)  # type: ignore[attr-defined]

    _login(raw_client, _OWNER)
    collection_id = raw_client.post(
        "/api/v1/collections", json={"name": "Owner's collection", "kind": "manual"}
    ).json()["id"]
    upload = raw_client.post(
        "/api/v1/materials", files={"file": ("calculus.pdf", _make_pdf(), "application/pdf")}
    ).json()

    _login(raw_client, _INTRUDER)
    yield {
        "collection_id": collection_id,
        "material_id": upload["material_id"],
        "job_id": upload["job_id"],
    }
    raw_client.app.dependency_overrides.clear()  # type: ignore[attr-defined]


# (method, path template, body) for every route that takes an owned id.
_ID_ROUTES: list[tuple[str, str, dict[str, Any] | None]] = [
    ("GET", "/api/v1/collections/{collection_id}", None),
    ("PUT", "/api/v1/collections/{collection_id}/materials", {"material_refs": []}),
    ("GET", "/api/v1/collections/{collection_id}/narrative", None),
    ("POST", "/api/v1/collections/{collection_id}/game", None),
    ("POST", "/api/v1/collections/{collection_id}/diagrams", None),
    ("GET", "/api/v1/collections/{collection_id}/chat", None),
    ("POST", "/api/v1/collections/{collection_id}/chat", {"message": "hi"}),
    ("GET", "/api/v1/materials/{material_id}", None),
    ("GET", "/api/v1/materials/{material_id}/tree", None),
    ("GET", "/api/v1/materials/{material_id}/sections/1", None),
    ("GET", "/api/v1/jobs/{job_id}", None),
]


@pytest.mark.parametrize(
    ("method", "path", "body"), _ID_ROUTES, ids=[f"{m} {p}" for m, p, _ in _ID_ROUTES]
)
def test_another_owners_resource_is_404(
    raw_client: TestClient,
    owned_ids: dict[str, str],
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    response = raw_client.request(method, path.format(**owned_ids), json=body)

    assert response.status_code == 404, response.text
    assert response.headers["content-type"] == "application/problem+json"


def test_the_owner_can_reach_what_the_intruder_cannot(
    raw_client: TestClient, owned_ids: dict[str, str]
) -> None:
    """Guards the matrix above against passing for the wrong reason: if
    these ids were simply wrong, every probe would 404 no matter how
    scoping behaved."""
    _login(raw_client, _OWNER)

    assert raw_client.get(f"/api/v1/collections/{owned_ids['collection_id']}").status_code == 200
    assert raw_client.get(f"/api/v1/materials/{owned_ids['material_id']}").status_code == 200
    assert raw_client.get(f"/api/v1/jobs/{owned_ids['job_id']}").status_code == 200
