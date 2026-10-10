"""End-to-end API smoke tests: upload → structure → study → game → chat → delete."""
import re

import pymupdf as fitz

from tests.conftest import FakeLLM, make_pdf


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_upload_uses_pdf_outline_with_stable_ids(client, book):
    assert book["num_pages"] == 12
    assert [c["id"] for c in book["chapters"]] == ["ch1", "ch2", "ch3"]

    intro, advanced, appendix = book["chapters"]
    assert [(s["id"], s["start_page"], s["end_page"]) for s in intro["sections"]] == [
        ("ch1.s1", 2, 3), ("ch1.s2", 4, 5)]
    # chapter without sub-sections becomes a single section spanning the chapter
    assert advanced["sections"] == [
        {"id": "ch2.s1", "title": "Advanced", "start_page": 6, "end_page": 9}]
    assert appendix["sections"][-1]["end_page"] == 12

    listed = client.get("/books").json()
    assert any(b["file_id"] == book["file_id"] and b["section_count"] == 4 for b in listed)


def test_upload_without_toc_falls_back_to_single_section(client):
    r = client.post("/books", files={"file": ("notoc.pdf", make_pdf(5, outline=False), "application/pdf")})
    assert r.status_code == 201
    chapters = r.json()["chapters"]
    assert len(chapters) == 1 and chapters[0]["sections"][0]["end_page"] == 5


def test_rejects_non_pdf_and_bad_user_id(client):
    assert client.post("/books", files={"file": ("x.txt", b"hi", "text/plain")}).status_code == 400
    assert client.get("/books", headers={"X-User-Id": "../etc"}).status_code == 400


def test_section_pdf_contains_only_section_pages(client, book):
    r = client.get(f"/books/{book['file_id']}/sections/ch1.s2/pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert len(doc) == 2 and "Page 4" in doc[0].get_text()
    assert client.get(f"/books/{book['file_id']}/sections/nope/pdf").status_code == 404


def test_study_materials_generated_once_then_cached(client, book, llm):
    url = f"/books/{book['file_id']}/sections/ch1.s1/study"
    assert client.get(url).status_code == 404

    first = client.post(url, json={})
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["narrative"] == FakeLLM.NARRATIVE
    assert body["game_code"] == FakeLLM.VALID_GAME
    assert body["diagrams"] and body["diagrams"][0].startswith("graph TD")

    calls = len(llm.calls)
    assert client.post(url, json={}).json() == body
    assert client.get(url).json() == body
    assert len(llm.calls) == calls, "cached request must not call the LLM"

    client.post(url, json={"force_regenerate": True})
    assert len(llm.calls) > calls


def test_game_agent_writes_the_game_artifact(client, book, llm):
    base = f"/books/{book['file_id']}/sections/ch2.s1"
    assert client.post(f"{base}/game").status_code == 409  # nothing generated yet

    client.post(f"{base}/study", json={})
    first = client.get(f"{base}/study").json()
    llm.tool_calls = [[("write_game", {"code": "```js\n" + BROKEN_GAME + "\n```"})]]
    r = client.post(f"{base}/game")
    assert r.status_code == 200, r.text
    assert r.json() == {"game_code": BROKEN_GAME, "game_version": first["game_version"] + 1}
    task = llm.conversations[-1]  # the agent's final turn, after its write
    assert [m.type for m in task] == ["system", "human", "ai", "tool"]
    assert "write_game" in task[0].content and "A clicking game" in task[1].content
    assert client.get(f"{base}/study").json()["game_code"] == BROKEN_GAME


BROKEN_GAME = (
    'const [on, setOn] = useState(false);\n'
    'if (!on) return React.createElement("button", {onClick: () => setOn(true)}, "Start");\n'
    'return React.createElement("div", null, panel.title);'
)


def test_browser_error_fixed_with_an_edit_in_the_same_conversation(client, book, llm):
    base = f"/books/{book['file_id']}/sections/ch1.s2"
    assert client.post(f"{base}/game/fix", json={"error": "x", "version": 0}).status_code == 409

    client.post(f"{base}/study", json={})
    llm.tool_calls = [[("write_game", {"code": BROKEN_GAME})]]
    version = client.post(f"{base}/game").json()["game_version"]

    llm.tool_calls = [[("edit_game", {"old_text": "panel.title", "new_text": '"Playing"'})]]
    report = {"error": "ReferenceError: panel is not defined", "version": version, "line": 3,
              "phase": "runtime", "stack": "ReferenceError: panel is not defined\n    at onClick (learnai-game.js:6:9)"}
    r = client.post(f"{base}/game/fix", json=report)
    assert r.status_code == 200, r.text
    fixed = BROKEN_GAME.replace("panel.title", '"Playing"')
    assert r.json() == {"game_code": fixed, "game_version": version + 1}
    assert client.get(f"{base}/study").json()["game_code"] == fixed

    # The agent continued its conversation: the task, its write, the error, then its edit
    convo = llm.conversations[-1]
    assert [m.type for m in convo] == ["system", "human", "ai", "tool", "ai", "human", "ai", "tool"]
    assert convo[2].tool_calls[0]["name"] == "write_game"
    assert convo[6].tool_calls[0]["name"] == "edit_game"
    error = convo[5].content
    assert "while being played" in error and "panel is not defined" in error
    assert 'At line 3: return React.createElement("div", null, panel.title);' in error

    # A report about the version before the fix gets the fixed game, without the agent
    calls = len(llm.calls)
    stale = client.post(f"{base}/game/fix", json=report)
    assert stale.json() == {"game_code": fixed, "game_version": version + 1}
    assert len(llm.calls) == calls


def test_new_game_starts_a_new_conversation(client, book, llm):
    base = f"/books/{book['file_id']}/sections/ch1.s2"
    client.post(f"{base}/study", json={})
    old = client.post(f"{base}/game").json()["game_version"]
    new = client.post(f"{base}/game").json()
    assert new["game_version"] > old  # versions only go up, across games
    assert [m.type for m in llm.conversations[-1]] == ["system", "human", "ai", "tool"]


def test_chat_persists_role_content_history(client, book, llm):
    base = f"/books/{book['file_id']}/sections/ch1.s1/chat"
    assert client.get(base).json() == {"history": []}

    r = client.post(base, json={"message": "What is this about?"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["history"][0] == {"role": "user", "content": "What is this about?"}
    assert data["history"][1]["role"] == "assistant" and data["reply"]
    assert client.get(base).json()["history"] == data["history"]



def test_chat_tutor_agent_sees_context_then_history(client, book, llm):
    base = f"/books/{book['file_id']}/sections/ch1.s1/chat"
    first = client.post(base, json={"message": "What is this about?"}).json()["reply"]
    assert first == "(fake tutor) Here is a concise answer."
    client.post(base, json={"message": "And then?"})

    conversation = llm.conversations[-1]
    assert [m.type for m in conversation] == ["system", "human", "ai", "human"]
    assert "You are LearnAI" in conversation[0].content
    assert re.search(rf'source="{book["file_id"]}/ch1\.s1": Sample Book: 1\.1 Basics \(\d+ characters\)',
                     conversation[0].content)
    assert [m.content for m in conversation[1:]] == ["What is this about?", first, "And then?"]

def test_chat_stream_speaks_ai_sdk_protocol(client, book, llm):
    import json
    base = f"/books/{book['file_id']}/sections/ch1.s1/chat"
    with client.stream("POST", f"{base}/stream", json={"message": "Explain it"}) as r:
        assert r.status_code == 200, r.read()
        assert r.headers["x-vercel-ai-ui-message-stream"] == "v1"
        frames = [f.removeprefix("data: ") for f in r.read().decode().strip().split("\n\n")]

    assert frames[-1] == "[DONE]"
    chunks = [json.loads(f) for f in frames[:-1]]
    types = [c["type"] for c in chunks]
    assert types[0] == "start" and types[-1] == "finish" and "error" not in types
    assert "data-stage" in types and all(c["transient"] for c in chunks if c["type"] == "data-stage")
    deltas = [c["delta"] for c in chunks if c["type"] == "text-delta"]
    assert len(deltas) > 1
    assert types.index("text-start") < types.index("text-delta") and "text-end" in types

    history = client.get(base).json()["history"]
    assert history[0] == {"role": "user", "content": "Explain it"}
    assert history[1] == {"role": "assistant", "content": "".join(deltas)}



def test_chat_tutor_searches_materials_before_answering(client, book, llm):
    import json
    llm.tool_calls = [[("search_materials", {"query": "topic"})]]
    base = f"/books/{book['file_id']}/sections/ch1.s1/chat"
    with client.stream("POST", f"{base}/stream", json={"message": "What's the topic?"}) as r:
        chunks = [json.loads(f.removeprefix("data: ")) for f in r.read().decode().strip().split("\n\n")[:-1]]

    stages = [c["data"] for c in chunks if c["type"] == "data-stage"]
    assert stages.index("search_materials") < stages.index("tools") < stages.index("tutor")
    result = llm.conversations[-1][-1]
    assert result.type == "tool" and f'source="{book['file_id']}/' in result.content

    reply = "".join(c["delta"] for c in chunks if c["type"] == "text-delta")
    assert reply == "(fake tutor) Here is a concise answer."
    assert client.get(base).json()["history"][1] == {"role": "assistant", "content": reply}

def test_delete_book_removes_everything(client, llm):
    r = client.post("/books", files={"file": ("tmp.pdf", make_pdf(3, outline=False), "application/pdf")})
    file_id = r.json()["file_id"]
    client.post(f"/books/{file_id}/sections/ch1.s1/study", json={})
    assert client.delete(f"/books/{file_id}").status_code == 204
    assert client.get(f"/books/{file_id}").status_code == 404
    assert all(b["file_id"] != file_id for b in client.get("/books").json())


def test_profile_questionnaire_roundtrip(client, llm):
    q = client.get("/profile/questionnaire").json()
    answers = {cat: {stmt: 4 for stmt in stmts} for cat, stmts in q["categories"].items()}
    r = client.put("/profile", json={"answers": answers})
    assert r.status_code == 200, r.text
    assert r.json()["answers"] == answers and r.json()["description"]
    assert client.get("/profile").json() == r.json()


def test_collection_study_over_book_sections(client, book, llm):
    col = client.post("/collections", json={
        "name": "Mix",
        "materials": {"textbook_sections": [
            {"file_id": book["file_id"], "section_id": "ch1.s1"},
            {"file_id": book["file_id"], "section_id": "ch1.s2"},
        ]},
    }).json()
    r = client.post(f"/collections/{col['collection_id']}/study", json={})
    assert r.status_code == 200, r.text
    assert r.json()["narrative"]


def _parse_sse(raw: str):
    import json
    events = []
    for frame in raw.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in frame.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_study_stream_emits_tokens_stages_and_done(client, book, llm):
    url = f"/books/{book['file_id']}/sections/ch1.s2/study/stream"
    with client.stream("POST", url, json={}) as r:
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
        events = _parse_sse(r.read().decode())

    tokens = [d for e, d in events if e == "token"]
    stages = [d for e, d in events if e == "stage"]
    assert len(tokens) > 1 and "".join(tokens) == FakeLLM.NARRATIVE
    assert stages[:3] == ["load_cached", "rag", "narrative"] and stages[-1] == "save"
    assert events[-1][0] == "done" and events[-1][1]["narrative"] == FakeLLM.NARRATIVE

    # second request is a cache hit: no tokens, immediate done
    with client.stream("POST", url, json={}) as r:
        cached = _parse_sse(r.read().decode())
    assert [e for e, _ in cached] == ["stage", "done"]
    assert cached[-1][1] == events[-1][1]
