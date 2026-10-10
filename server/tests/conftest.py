"""
Test fixtures: an isolated DATA_DIR, deterministic fake embeddings, and a
scripted fake LLM — so the full HTTP → agent → storage/RAG path runs offline.
"""
import hashlib
import json
import os
import re
import tempfile
import time
from typing import Any, Callable

import pytest

_DATA = tempfile.mkdtemp(prefix="learnai-test-")
os.environ["DATA_DIR"] = _DATA
os.environ["CHROMA_DIR"] = os.path.join(_DATA, "vectorstore")

import pymupdf as fitz  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from langchain_core.language_models import BaseChatModel  # noqa: E402
from langchain_core.messages import AIMessage, AIMessageChunk  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult  # noqa: E402

import core.vectorstore  # noqa: E402


def _fake_embed(texts):
    out = []
    for t in texts:
        h = hashlib.sha256(t.encode()).digest()
        out.append([b / 255 for b in h[:16]])
    return out


# conftest can be imported twice (as `conftest` and `tests.conftest`); keep the original once
if not hasattr(core.vectorstore, "_real_embed"):
    core.vectorstore._real_embed = core.vectorstore._embed
REAL_EMBED = core.vectorstore._real_embed
core.vectorstore._embed = _fake_embed


class FakeLLM:
    """Answers by prompt type; game code can be scripted per call."""

    VALID_GAME = 'const [n, setN] = useState(0);\nreturn React.createElement("button", {onClick: () => setN(n + 1)}, `Clicks: ${n}`);'
    NARRATIVE = "## Narrative\nPersonalized explanation of this section."

    def __init__(self):
        self.calls = []
        self.conversations = []  # every call's full message list
        self.game_codes = []
        self.tool_calls = []  # per answer to a human turn: [(tool name, args), ...] to call first

    def __call__(self, prompt: str) -> str:
        self.calls.append(prompt)
        if "Create a fully functional React component" in prompt or "breaks when the game is played" in prompt:
            return self.game_codes.pop(0) if self.game_codes else self.VALID_GAME
        if "latest question" in prompt:
            return "(fake tutor) Here is a concise answer."
        if "mermaid" in prompt.lower():
            return "```mermaid\ngraph TD\n  A[Start] --> B[End]\n```"
        if "game" in prompt.lower():
            return "A clicking game about the section."
        return self.NARRATIVE


class FakeChatModel(BaseChatModel):
    """LangChain chat model backed by a FakeLLM; streams word by word."""

    responder: Callable[[str], str]
    token_delay: float = 0.0  # seconds per streamed token, to make streaming visible in UI runs

    @property
    def _llm_type(self) -> str:
        return "fake-chat"

    def bind_tools(self, tools, **kwargs):
        return self

    def _tool_calls(self, messages):
        """Scripted tool calls to answer a human turn with, if any."""
        if isinstance(self.responder, FakeLLM) and self.responder.tool_calls and messages[-1].type == "human":
            self.responder.conversations.append(list(messages))
            calls = self.responder.tool_calls.pop(0)
            return [{"name": name, "args": args, "id": f"call-{i}"} for i, (name, args) in enumerate(calls)]
        return None

    def _reply(self, messages) -> str:
        if isinstance(self.responder, FakeLLM):
            self.responder.conversations.append(list(messages))
        # A system prompt (the tutor's) is read along with the latest message
        prompt = "\n\n".join(str(m.content) for m in messages if m.type == "system")
        content: Any = messages[-1].content
        prompt += content if isinstance(content, str) else str(content)
        return self.responder(prompt)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        calls = self._tool_calls(messages)
        if calls:
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content="", tool_calls=calls))])
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self._reply(messages)))])

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        calls = self._tool_calls(messages)
        if calls:
            chunks = [{"name": c["name"], "args": json.dumps(c["args"]), "id": c["id"], "index": i}
                      for i, c in enumerate(calls)]
            yield ChatGenerationChunk(message=AIMessageChunk(content="", tool_call_chunks=chunks))
            return
        for token in re.findall(r"\S+\s*", self._reply(messages)):
            if self.token_delay:
                time.sleep(self.token_delay)
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=token))
            if run_manager:
                run_manager.on_llm_new_token(token, chunk=chunk)
            yield chunk


def install_fake_llm(fake: FakeLLM, setattr_: Callable = setattr, token_delay: float = 0.0) -> None:
    """Route every core.llm model construction to the fake."""
    import core.llm

    setattr_(core.llm, "get_llm", lambda *args, **kwargs: FakeChatModel(responder=fake, token_delay=token_delay))


@pytest.fixture
def llm(monkeypatch):
    fake = FakeLLM()
    install_fake_llm(fake, monkeypatch.setattr)
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
