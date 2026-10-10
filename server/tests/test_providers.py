"""
Provider tests against a fake OpenAI-compatible server (the vLLM stand-in):
the real langchain-openai / openai clients are exercised end to end.
"""
import io
import json
import wave

import pytest

import core.llm
import core.vectorstore
import services.media_service
from core.config import settings
from tests.conftest import REAL_EMBED, FakeLLM, make_pdf
from tests.fake_openai import FakeOpenAIServer

CHAT_MODEL = "Qwen/Qwen2.5-VL-7B-Instruct"


@pytest.fixture
def vllm(monkeypatch):
    with FakeOpenAIServer(FakeLLM(), models=[CHAT_MODEL, settings.EMBEDDING_MODEL, settings.STT_MODEL]) as server:
        for key in ("OPENAI_BASE_URL", "EMBEDDING_BASE_URL", "STT_BASE_URL"):
            monkeypatch.setattr(settings, key, server.base_url)
        monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
        monkeypatch.setattr(settings, "LLM_MODEL", "")
        for cached in (core.llm._served_model, core.vectorstore._openai_client, services.media_service._openai_client):
            cached.cache_clear()
        yield server
        for cached in (core.llm._served_model, core.vectorstore._openai_client, services.media_service._openai_client):
            cached.cache_clear()


def test_llm_uses_served_model_and_caps_tokens(vllm, monkeypatch):
    monkeypatch.setattr(settings, "LLM_MAX_OUTPUT_TOKENS", 1000)
    model = core.llm.get_llm(max_tokens=8192)
    assert model.model_name == CHAT_MODEL and model.max_tokens == 1000
    assert core.llm.invoke_llm("Write a game idea") == "A clicking game about the section."
    sent = vllm.requests[-1]
    assert sent.get("max_completion_tokens", sent.get("max_tokens")) == 1000


def test_message_text_drops_reasoning():
    from langchain_core.messages import AIMessage
    assert core.llm.message_text(AIMessage(content="<think>hmm</think>\nAnswer")) == "Answer"


def test_study_stream_over_openai_provider(client, book, vllm):
    url = f"/books/{book['file_id']}/sections/ch1.s1/study/stream"
    with client.stream("POST", url, json={}) as r:
        raw = r.read().decode()
    tokens = [json.loads(f.split("data: ", 1)[1]) for f in raw.split("\n\n") if f.startswith("event: token")]
    assert len(tokens) > 1 and "".join(tokens) == FakeLLM.NARRATIVE
    assert "event: done" in raw
    assert any(req.get("stream") for req in vllm.requests if req["path"] == "chat")


def test_remote_embeddings_batched(vllm, monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "openai")
    monkeypatch.setattr(settings, "EMBEDDING_BATCH_SIZE", 2)
    vectors = REAL_EMBED(["a", "b", "c"])
    assert len(vectors) == 3 and len(vectors[0]) == 8
    assert [r["count"] for r in vllm.requests if r["path"] == "embeddings"] == [2, 1]


def test_local_embeddings_load_once_and_encode_serially(monkeypatch):
    # Background indexing and request-time RAG embed concurrently; two loads or
    # overlapping encodes on MPS segfault the process
    import functools
    import threading
    import time

    import numpy as np

    loads, active, overlaps = [], [], []

    class FakeModel:
        def encode(self, texts, show_progress_bar=False):
            active.append(1)
            overlaps.append(len(active) > 1)
            time.sleep(0.01)
            active.pop()
            return np.zeros((len(texts), 4))

    def load():
        loads.append(1)
        time.sleep(0.05)
        return FakeModel()

    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "local")
    monkeypatch.setattr(core.vectorstore, "_local_model", functools.lru_cache(maxsize=1)(load))
    threads = [threading.Thread(target=REAL_EMBED, args=(["x"],)) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(loads) == 1
    assert len(overlaps) == 8 and not any(overlaps)


def test_chroma_client_opened_once_under_concurrency(monkeypatch):
    import functools
    import threading
    import time

    opens = []

    def open_client():
        opens.append(1)
        time.sleep(0.05)
        return object()

    monkeypatch.setattr(core.vectorstore, "_open_chroma_client", functools.lru_cache(maxsize=1)(open_client))
    clients = []
    threads = [threading.Thread(target=lambda: clients.append(core.vectorstore._chroma_client())) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(opens) == 1
    assert len(clients) == 8 and len(set(map(id, clients))) == 1


def test_collection_names_fit_chroma_limits():
    name = core.vectorstore._collection_name("u" * 64, "documents")
    assert len(name) <= 63
    assert name != core.vectorstore._collection_name("u" * 64, "other")


def _wav(seconds: float = 0.5) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * int(16000 * seconds))
    return buf.getvalue()


def test_remote_transcription(vllm, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "STT_PROVIDER", "openai")
    audio = tmp_path / "lecture.wav"
    audio.write_bytes(_wav())
    text = services.media_service.transcribe_file(audio)
    stt = [r for r in vllm.requests if r["path"] == "transcriptions"]
    assert stt and stt[0]["model"] == settings.STT_MODEL and stt[0]["size"] > 0
    assert text.startswith("transcribed ")


def test_vision_toc_over_openai_provider(client, vllm):
    r = client.post("/books", data={"toc_pages": "1-1"},
                    files={"file": ("scan.pdf", make_pdf(6, outline=False), "application/pdf")})
    assert r.status_code == 201, r.text
    assert [c["title"] for c in r.json()["chapters"]] == ["Scanned One", "Scanned Two"]
    vision = [q for q in vllm.requests if q["path"] == "chat"][-1]
    parts = vision["messages"][-1]["content"]
    assert any(p["type"] == "image_url" and p["image_url"]["url"].startswith("data:image/jpeg;base64,")
               for p in parts)


def test_vision_disabled_imports_single_section(client, monkeypatch):
    monkeypatch.setattr(settings, "LLM_VISION_ENABLED", False)
    r = client.post("/books", data={"toc_pages": "1-1"},
                    files={"file": ("scan.pdf", make_pdf(4, outline=False), "application/pdf")})
    assert r.status_code == 201
    assert len(r.json()["chapters"]) == 1


def test_dependencies_health(client, vllm, monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "openai")
    monkeypatch.setattr(settings, "STT_PROVIDER", "openai")
    body = client.get("/health/dependencies").json()
    assert body["ok"] and body["llm"]["served"][0] == CHAT_MODEL

    monkeypatch.setattr(settings, "LLM_MODEL", "missing-model")
    body = client.get("/health/dependencies").json()
    assert not body["ok"] and "not served" in body["llm"]["error"]


def test_dependencies_health_reports_unreachable(client, monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_BASE_URL", "http://127.0.0.1:9/v1")
    body = client.get("/health/dependencies").json()
    assert not body["ok"] and body["llm"]["error"]


def test_ready_and_upload_limit(client, monkeypatch):
    assert client.get("/health/ready").json() == {"status": "ready"}
    big = b"0" * (2 * 1024 * 1024)
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 1)
    # the limit is read when the app is built, so check against a fresh app
    from fastapi.testclient import TestClient
    from main import create_app
    with TestClient(create_app()) as fresh:
        r = fresh.post("/books", files={"file": ("big.pdf", big, "application/pdf")})
    assert r.status_code == 413


def test_clip_source(monkeypatch):
    from utils.prompt_utils import clip_source
    monkeypatch.setattr(settings, "LLM_MAX_SOURCE_CHARS", 10)
    assert clip_source("short") == "short"
    assert clip_source("x" * 50).startswith("x" * 10) and "truncated" in clip_source("x" * 50)


def test_budgets_follow_context_length(vllm, monkeypatch):
    monkeypatch.setattr(settings, "LLM_MAX_OUTPUT_TOKENS", None)
    monkeypatch.setattr(settings, "LLM_MAX_SOURCE_CHARS", None)
    monkeypatch.setattr(settings, "LLM_CONTEXT_TOKENS", 131_072)
    assert settings.max_output_tokens == 32_768
    assert settings.max_source_chars == 209_715
    monkeypatch.setattr(settings, "LLM_CONTEXT_TOKENS", 32_768)
    assert settings.max_output_tokens == 8192
    assert core.llm.get_llm(max_tokens=32_768).max_tokens == 8192

    monkeypatch.setattr(settings, "LLM_MAX_OUTPUT_TOKENS", 2000)
    monkeypatch.setattr(settings, "LLM_MAX_SOURCE_CHARS", 5000)
    assert (settings.max_output_tokens, settings.max_source_chars) == (2000, 5000)
