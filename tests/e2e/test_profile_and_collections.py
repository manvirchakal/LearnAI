"""Profile and collections routers, exercised through the real app with an
authenticated session — same fake-db/settings-override pattern as
``tests/e2e/test_auth.py``, plus a real login so ``CurrentUser`` resolves.
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from learnai.config import LLMTask, Settings, get_settings
from learnai.deps import get_db, get_llm_client
from learnai.main import create_app
from learnai.services.auth.google_verifier import GoogleIdentity
from tests.fakes.llm import FakeLLMClient
from tests.fakes.mongo import FakeAsyncDatabase

_IDENTITY = GoogleIdentity(
    sub="google-sub-1", email="ada@example.com", name="Ada Lovelace", picture=None
)
_FAKE_DESCRIPTION = "You learn best through vivid diagrams and visual demonstrations."


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
    raw_client.app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient(  # type: ignore[attr-defined]
        completions={LLMTask.profile_description: _FAKE_DESCRIPTION}
    )
    with patch("learnai.routers.auth.verify_google_id_token", return_value=_IDENTITY):
        login = raw_client.post("/auth/google", json={"id_token": "whatever"})
    assert login.status_code == 200

    yield raw_client
    raw_client.app.dependency_overrides.clear()  # type: ignore[attr-defined]


class TestProfileRouter:
    def test_get_before_submission_returns_null(self, client: TestClient) -> None:
        response = client.get("/api/v1/profile")
        assert response.status_code == 200
        assert response.json() is None

    def test_submit_then_get_roundtrips(self, client: TestClient) -> None:
        submission = {
            "answers": {"Visual": [1, 2]},
            "scores": {"visual": 0.8},
            "questionnaire_version": 1,
        }
        put_response = client.put("/api/v1/profile", json=submission)
        assert put_response.status_code == 200
        assert put_response.json()["description"] == _FAKE_DESCRIPTION

        get_response = client.get("/api/v1/profile")
        assert get_response.status_code == 200
        body = get_response.json()
        assert body["scores"] == {"visual": 0.8}
        assert body["questionnaire_version"] == 1

    def test_requires_authentication(self, client: TestClient) -> None:
        client.cookies.clear()
        assert client.get("/api/v1/profile").status_code == 401


class TestCollectionsRouter:
    def test_create_then_list_then_get(self, client: TestClient) -> None:
        create_response = client.post(
            "/api/v1/collections", json={"name": "Calculus", "kind": "manual"}
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["name"] == "Calculus"
        assert created["material_refs"] == []
        assert created["parent_collection_id"] is None

        list_response = client.get("/api/v1/collections")
        assert list_response.status_code == 200
        assert any(c["id"] == created["id"] for c in list_response.json())

        get_response = client.get(f"/api/v1/collections/{created['id']}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == created["id"]

    def test_get_of_missing_collection_is_404(self, client: TestClient) -> None:
        response = client.get(f"/api/v1/collections/{ObjectId()}")
        assert response.status_code == 404

    def test_get_with_malformed_id_is_422(self, client: TestClient) -> None:
        response = client.get("/api/v1/collections/not-an-object-id")
        assert response.status_code == 422

    def test_parent_child_relationship_via_api(self, client: TestClient) -> None:
        chapter = client.post(
            "/api/v1/collections", json={"name": "Chapter 1", "kind": "chapter"}
        ).json()
        section = client.post(
            "/api/v1/collections",
            json={
                "name": "1.1 Limits",
                "kind": "section",
                "parent_collection_id": chapter["id"],
            },
        ).json()

        assert section["parent_collection_id"] == chapter["id"]

    def test_update_materials(self, client: TestClient) -> None:
        created = client.post(
            "/api/v1/collections", json={"name": "Calculus", "kind": "manual"}
        ).json()
        material_id = str(ObjectId())

        response = client.put(
            f"/api/v1/collections/{created['id']}/materials",
            json={"material_refs": [{"material_id": material_id, "section_ids": []}]},
        )
        assert response.status_code == 200
        refs = response.json()["material_refs"]
        assert len(refs) == 1
        assert refs[0]["material_id"] == material_id
        assert refs[0]["added_at"] is not None

    def test_update_materials_section_ids_are_tree_node_ids_not_object_ids(
        self, client: TestClient
    ) -> None:
        """section_ids are document-tree node_ids (e.g. "1.2" — see
        schemas.documents.TreeNode), not ObjectIds. Regression test: an
        earlier version of this endpoint parsed them as ObjectId, which
        would 422 on any real section reference."""
        created = client.post(
            "/api/v1/collections", json={"name": "Calculus", "kind": "manual"}
        ).json()
        material_id = str(ObjectId())

        response = client.put(
            f"/api/v1/collections/{created['id']}/materials",
            json={"material_refs": [{"material_id": material_id, "section_ids": ["1", "1.2"]}]},
        )
        assert response.status_code == 200
        assert response.json()["material_refs"][0]["section_ids"] == ["1", "1.2"]

    def test_another_owners_collection_is_a_404_not_a_403(
        self, client: TestClient, raw_client: TestClient
    ) -> None:
        """No existence oracle: owner B's request for owner A's collection
        looks identical to a collection that doesn't exist at all."""
        created = client.post(
            "/api/v1/collections", json={"name": "Owner A's notes", "kind": "manual"}
        ).json()

        raw_client.cookies.clear()
        other_identity = GoogleIdentity(
            sub="google-sub-2", email="bob@example.com", name="Bob", picture=None
        )
        with patch("learnai.routers.auth.verify_google_id_token", return_value=other_identity):
            login = raw_client.post("/auth/google", json={"id_token": "whatever"})
        assert login.status_code == 200

        response = raw_client.get(f"/api/v1/collections/{created['id']}")
        assert response.status_code == 404

    def test_requires_authentication(self, client: TestClient) -> None:
        client.cookies.clear()
        assert client.get("/api/v1/collections").status_code == 401
