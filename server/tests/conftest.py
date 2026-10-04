"""
Test fixtures: an isolated DATA_DIR, deterministic fake embeddings, and a
scripted fake LLM — so the full HTTP → agent → storage/RAG path runs offline.
"""
import hashlib
import os
import sys
import tempfile
import types

import pytest

_DATA = tempfile.mkdtemp(prefix="learnai-test-")
os.environ["DATA_DIR"] = _DATA
os.environ["CHROMA_DIR"] = os.path.join(_DATA, "vectorstore")

# Heavy ML deps are optional for tests: stub them if they aren't installed.
for name, attr in (("sentence_transformers", "SentenceTransformer"), ("faster_whisper", "WhisperModel")):
    try:
        __import__(name)
    except ImportError:
        mod = types.ModuleType(name)
        setattr(mod, attr, object)
        sys.modules[name] = mod

import fitz  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import core.vectorstore  # noqa: E402


def _fake_embed(texts):
    out = []
    for t in texts:
        h = hashlib.sha256(t.encode()).digest()
        out.append([b / 255 for b in h[:16]])
    return out


core.vectorstore._embed = _fake_embed


class FakeLLM:
    """Answers by prompt type; game code can be scripted per call."""

    VALID_GAME = 'const [n, setN] = useState(0);\nreturn React.createElement("button", {onClick: () => setN(n + 1)}, `Clicks: ${n}`);'

    def __init__(self):
        self.calls = []
        self.game_codes = []

    def __call__(self, prompt, *args, **kwargs):
        self.calls.append(prompt)
        if "Create a fully functional React component" in prompt:
            return self.game_codes.pop(0) if self.game_codes else self.VALID_GAME
        if "mermaid" in prompt.lower():
            return "```mermaid\ngraph TD\n  A[Start] --> B[End]\n```"
        if "game" in prompt.lower():
            return "A clicking game about the section."
        return "## Narrative\nPersonalized explanation."


@pytest.fixture
def llm(monkeypatch):
    fake = FakeLLM()
    import agents.content_agent as content
    import agents.chat_agent as chat
    import services.profile_service as profile

    monkeypatch.setattr(content, "invoke_llm", fake)
    monkeypatch.setattr(chat, "invoke_llm_with_history", lambda prompt, history, **kw: fake(prompt))
    monkeypatch.setattr(profile, "invoke_llm", fake, raising=False)
    return fake


@pytest.fixture
def client():
    from main import app
    with TestClient(app) as c:
        yield c


def make_pdf(pages: int = 12, outline: bool = True) -> bytes:
    doc = fitz.open()
    for i in range(1, pages + 1):
        doc.new_page().insert_text((72, 72), f"Page {i} content about topic {i}.")
    if outline:
        doc.set_toc([
            [1, "Intro", 1],
            [2, "1.1 Basics", 2],
            [2, "1.2 More", 4],
            [1, "Advanced", 6],
            [1, "Appendix", 10],
            [2, "A.1 Tables", 11],
        ])
    return doc.tobytes()


@pytest.fixture
def book(client):
    r = client.post("/books", files={"file": ("Sample Book.pdf", make_pdf(), "application/pdf")})
    assert r.status_code == 201, r.text
    return r.json()
