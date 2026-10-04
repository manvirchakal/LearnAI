"""End-to-end API smoke tests: upload → structure → study → game → chat → delete."""
import fitz

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


def test_game_code_retries_until_valid(client, book, llm):
    base = f"/books/{book['file_id']}/sections/ch2.s1"
    assert client.post(f"{base}/game").status_code == 409  # nothing generated yet

    client.post(f"{base}/study", json={})
    llm.game_codes = ["return React.createElement(", "const = ;"]  # two syntax errors, then valid
    r = client.post(f"{base}/game")
    assert r.status_code == 200
    assert r.json()["game_code"] == FakeLLM.VALID_GAME
    assert llm.game_codes == [], "both invalid attempts should have been consumed by retries"
    assert client.get(f"{base}/study").json()["game_code"] == FakeLLM.VALID_GAME


def test_chat_persists_role_content_history(client, book, llm):
    base = f"/books/{book['file_id']}/sections/ch1.s1/chat"
    assert client.get(base).json() == {"history": []}

    r = client.post(base, json={"message": "What is this about?"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["history"][0] == {"role": "user", "content": "What is this about?"}
    assert data["history"][1]["role"] == "assistant" and data["reply"]
    assert client.get(base).json()["history"] == data["history"]


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
