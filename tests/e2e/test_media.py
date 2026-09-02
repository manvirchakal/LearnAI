"""Media router, exercised through the real app — same fake-db/storage/
ARQ pattern as ``tests/e2e/test_materials.py``. ``transcribe_lecture_task``/
``import_youtube_task`` are unit-tested against fakes in
``tests/unit/test_worker_media_tasks.py`` and never run in this process —
tests that need a lecture material past ``uploaded`` invoke the task
directly, standing in for what the real worker would do after draining
the (faked) queue.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from learnai.config import LLMTask, Settings, get_settings
from learnai.deps import (
    get_arq_pool,
    get_db,
    get_embedder,
    get_llm_client,
    get_storage,
    get_tts_engine,
    get_vector_store,
)
from learnai.main import create_app
from learnai.services.asr import TranscriptResult, TranscriptSegment
from learnai.services.auth.google_verifier import GoogleIdentity
from learnai.worker.tasks import import_youtube_task, transcribe_lecture_task
from tests.fakes.arq import FakeArqPool
from tests.fakes.asr import FakeASR
from tests.fakes.embedder import FakeEmbedder
from tests.fakes.llm import FakeLLMClient
from tests.fakes.mongo import FakeAsyncDatabase
from tests.fakes.storage import FakeStorage
from tests.fakes.tts import FakeTTS
from tests.fakes.vector_store import FakeVectorStore

_IDENTITY = GoogleIdentity(
    sub="google-sub-1", email="ada@example.com", name="Ada Lovelace", picture=None
)

_TRANSCRIPT = TranscriptResult(
    language="en",
    segments=[
        TranscriptSegment(start=0.0, end=2.0, text="Hello everyone."),
        TranscriptSegment(start=2.0, end=5.0, text="Today: limits."),
    ],
)


@pytest.fixture(scope="module")
def raw_client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def client(raw_client: TestClient) -> Iterator[TestClient]:
    raw_client.cookies.clear()
    fake_db = FakeAsyncDatabase()
    fake_storage = FakeStorage()
    fake_arq = FakeArqPool()
    fake_asr = FakeASR(result=_TRANSCRIPT)
    fake_tts = FakeTTS()
    fake_llm = FakeLLMClient(completions={LLMTask.translation: "Bonjour le monde"})

    overrides: dict[Any, Any] = {
        get_db: lambda: fake_db,
        get_settings: lambda: Settings(
            session_secret="a-test-secret-at-least-32-bytes-long",
            google_client_id="test-client-id",
        ),
        get_storage: lambda: fake_storage,
        get_arq_pool: lambda: fake_arq,
        get_embedder: lambda: FakeEmbedder(),
        get_vector_store: lambda: FakeVectorStore(),
        get_tts_engine: lambda: fake_tts,
        get_llm_client: lambda: fake_llm,
    }
    raw_client.app.dependency_overrides.update(overrides)  # type: ignore[attr-defined]

    with patch("learnai.routers.auth.verify_google_id_token", return_value=_IDENTITY):
        login = raw_client.post("/auth/google", json={"id_token": "whatever"})
    assert login.status_code == 200

    raw_client.app.state.fake_db = fake_db  # type: ignore[attr-defined]
    raw_client.app.state.fake_storage = fake_storage  # type: ignore[attr-defined]
    raw_client.app.state.fake_arq = fake_arq  # type: ignore[attr-defined]
    raw_client.app.state.fake_asr = fake_asr  # type: ignore[attr-defined]
    raw_client.app.state.fake_tts = fake_tts  # type: ignore[attr-defined]
    raw_client.app.state.owner_id = ObjectId(login.json()["id"])  # type: ignore[attr-defined]

    yield raw_client
    raw_client.app.dependency_overrides.clear()  # type: ignore[attr-defined]


def _upload_lecture(client: TestClient, *, content_type: str = "audio/mpeg") -> httpx.Response:
    response: httpx.Response = client.post(
        "/api/v1/media/lectures", files={"file": ("lecture1.mp3", b"fake-audio", content_type)}
    )
    return response


async def _run_lecture_job(client: TestClient, material_id: str, job_id: str) -> None:
    ctx = {
        "db": client.app.state.fake_db,  # type: ignore[attr-defined]
        "storage": client.app.state.fake_storage,  # type: ignore[attr-defined]
        "asr": client.app.state.fake_asr,  # type: ignore[attr-defined]
        "embedder": FakeEmbedder(),
        "vector_store": FakeVectorStore(),
        "settings": Settings(),
    }
    owner_id = client.app.state.owner_id  # type: ignore[attr-defined]
    await transcribe_lecture_task(
        ctx, owner_id=str(owner_id), material_id=material_id, job_id=job_id
    )


class TestUploadLecture:
    def test_upload_returns_202_with_poll_url(self, client: TestClient) -> None:
        response = _upload_lecture(client)

        assert response.status_code == 202
        body = response.json()
        assert body["poll_url"] == f"/api/v1/jobs/{body['job_id']}"

        material = client.get(f"/api/v1/materials/{body['material_id']}").json()
        assert material["status"] == "uploaded"
        assert material["kind"] == "lecture"

        fake_arq: FakeArqPool = client.app.state.fake_arq  # type: ignore[attr-defined]
        assert fake_arq.jobs == [
            {
                "function": "transcribe_lecture_task",
                "kwargs": {
                    "owner_id": str(client.app.state.owner_id),  # type: ignore[attr-defined]
                    "material_id": body["material_id"],
                    "job_id": body["job_id"],
                },
            }
        ]

    def test_upload_rejects_unsupported_content_type(self, client: TestClient) -> None:
        assert _upload_lecture(client, content_type="text/plain").status_code == 422

    def test_upload_rejects_empty_file(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/media/lectures", files={"file": ("empty.mp3", b"", "audio/mpeg")}
        )
        assert response.status_code == 422

    def test_upload_requires_authentication(self, client: TestClient) -> None:
        client.cookies.clear()
        assert _upload_lecture(client).status_code == 401

    async def test_transcription_makes_material_ready_and_readable(
        self, client: TestClient
    ) -> None:
        body = _upload_lecture(client).json()
        await _run_lecture_job(client, body["material_id"], body["job_id"])

        material = client.get(f"/api/v1/materials/{body['material_id']}").json()
        assert material["status"] == "toc_ready"

        tree = client.get(f"/api/v1/materials/{body['material_id']}/tree").json()
        assert len(tree["tree"]) == 1

        section = client.get(f"/api/v1/materials/{body['material_id']}/sections/1").json()
        assert section["text"] == "Hello everyone. Today: limits."


class TestYouTubeImport:
    def test_import_returns_202_with_poll_url(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/media/youtube", json={"url": "https://youtube.com/watch?v=abc123"}
        )

        assert response.status_code == 202
        body = response.json()
        assert body["poll_url"] == f"/api/v1/jobs/{body['job_id']}"

        material = client.get(f"/api/v1/materials/{body['material_id']}").json()
        assert material["kind"] == "lecture"
        assert material["status"] == "uploaded"

        fake_arq: FakeArqPool = client.app.state.fake_arq  # type: ignore[attr-defined]
        assert fake_arq.jobs == [
            {
                "function": "import_youtube_task",
                "kwargs": {
                    "owner_id": str(client.app.state.owner_id),  # type: ignore[attr-defined]
                    "material_id": body["material_id"],
                    "job_id": body["job_id"],
                    "url": "https://youtube.com/watch?v=abc123",
                },
            }
        ]

    def test_import_rejects_non_url(self, client: TestClient) -> None:
        response = client.post("/api/v1/media/youtube", json={"url": "not a url"})
        assert response.status_code == 422

    def test_import_requires_authentication(self, client: TestClient) -> None:
        client.cookies.clear()
        response = client.post(
            "/api/v1/media/youtube", json={"url": "https://youtube.com/watch?v=abc"}
        )
        assert response.status_code == 401

    async def test_full_import_makes_material_ready(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        body = client.post(
            "/api/v1/media/youtube", json={"url": "https://youtube.com/watch?v=abc123"}
        ).json()

        downloaded_path = tmp_path / "abc123.mp3"
        downloaded_path.write_bytes(b"fake-mp3-bytes")
        ctx = {
            "db": client.app.state.fake_db,  # type: ignore[attr-defined]
            "storage": client.app.state.fake_storage,  # type: ignore[attr-defined]
            "asr": client.app.state.fake_asr,  # type: ignore[attr-defined]
            "embedder": FakeEmbedder(),
            "vector_store": FakeVectorStore(),
            "settings": Settings(),
        }
        owner_id = client.app.state.owner_id  # type: ignore[attr-defined]
        with patch(
            "learnai.worker.tasks.download_audio",
            return_value=("Lecture 1: Limits", downloaded_path),
        ):
            await import_youtube_task(
                ctx,
                owner_id=str(owner_id),
                material_id=body["material_id"],
                job_id=body["job_id"],
                url="https://youtube.com/watch?v=abc123",
            )

        material = client.get(f"/api/v1/materials/{body['material_id']}").json()
        assert material["status"] == "toc_ready"
        assert material["filename"] == "Lecture 1: Limits.mp3"


class TestTranslate:
    def test_translate_returns_translated_text(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/media/translate", json={"text": "Hello world", "target_language": "fr-FR"}
        )

        assert response.status_code == 200
        assert response.json() == {"translated_text": "Bonjour le monde"}

    def test_translate_requires_authentication(self, client: TestClient) -> None:
        client.cookies.clear()
        response = client.post(
            "/api/v1/media/translate", json={"text": "Hello", "target_language": "fr-FR"}
        )
        assert response.status_code == 401

    def test_translate_rejects_empty_text(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/media/translate", json={"text": "", "target_language": "fr-FR"}
        )
        assert response.status_code == 422


class TestTTS:
    def test_tts_returns_audio_bytes(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/media/tts", json={"text": "Hello world", "language": "en-US"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/wav"
        assert response.content == b"fake-wav-bytes"

    def test_tts_requires_authentication(self, client: TestClient) -> None:
        client.cookies.clear()
        response = client.post("/api/v1/media/tts", json={"text": "Hello", "language": "en-US"})
        assert response.status_code == 401

    def test_tts_unsupported_language_is_422(self, client: TestClient) -> None:
        response = client.post("/api/v1/media/tts", json={"text": "Hello", "language": "xx-XX"})
        assert response.status_code == 422
