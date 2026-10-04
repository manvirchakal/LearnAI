# LearnAI

LearnAI turns a textbook PDF into a personalized study experience. For every section of a book it generates, tailored to the learner's VARK learning style:

- **Narrative.** A rewritten explanation that streams in as it is written.
- **Game.** An interactive React mini-game generated for the section.
- **Diagrams.** Mermaid diagrams of the key concepts.
- **Tutor chat.** Chat grounded in the section text plus retrieval over everything the learner has uploaded.

It can also transcribe YouTube videos and recorded lectures and ingest slide decks and notes, and it offers translation and text-to-speech.

All processing runs locally except the LLM itself: **Claude via AWS Bedrock** is the only cloud dependency.

| Concern | Implementation |
|---|---|
| PDF text, outline, page rendering | PyMuPDF |
| Printed table-of-contents parsing (when a PDF has no outline) | Claude vision |
| Speech-to-text | faster-whisper |
| Text-to-speech | pyttsx3 (espeak on Linux) |
| Translation | argostranslate (models download once per language pair) |
| Embeddings / RAG | sentence-transformers + ChromaDB |
| Storage | Local filesystem under `server/data/` |
| Auth | None yet: identity is the `X-User-Id` header (default `default`) |

## Architecture

```
client/  Next.js 14 (App Router) · React 18 · TypeScript · MUI 6 + Tailwind · TanStack Query · Zustand
  app/         routes: /home /upload /library /questionnaire /study/[fileId] /study/[fileId]/[sectionId]
  api/         typed hooks per backend resource (books, study, chat, profile, media, …)
  components/  ui/ (primitives) · layout/ · study/ · game/ · upload/ · library/ · shared/
  types/       API contracts mirrored from server/models
  store/       UI preferences only (server state lives in TanStack Query)

server/  FastAPI · LangGraph · FastMCP
  routes/      HTTP only: validation, status codes, response models
  agents/      LangGraph workflows: document ingestion, study content, chat, media
  services/    single-purpose operations: books, storage, RAG, media, profile, accessibility
  models/      Pydantic request/response models
  utils/       pure helpers: prompts, TOC normalization, game-code and diagram cleanup, SSE
  core/        config, local storage, vector store, Bedrock client
  mcp_server/  the same local services exposed as MCP tools, mounted at /mcp
  tests/       offline end-to-end API tests (fake LLM + embeddings)
```

**The study model.**
- **Books and sections.** An uploaded PDF becomes a *book*. Its outline (or Claude's reading of its printed TOC) is normalized into chapters and *sections*. Each section gets a stable id such as `ch3.s2` and an explicit page range. Sections are the unit of study, and every generated artifact is cached per section.
- **Collections.** Collections are an optional grouping of sections, transcripts, slides and notes. You can study and chat over them too.

**Agents.**
- **Document agent:** `save_upload → read_outline → (vision TOC) → normalize → save_metadata`. Section text is then indexed in the background.
- **Content agent:** `load_cached → rag → narrative → game_idea → game_code ⇄ validate_code → diagrams → save`. A cache hit short-circuits the run. Game code is syntax-checked and retried up to 2 times. A separate game-only graph regenerates just the game.
- **Chat agent:** `load_context → translate_input → rag_retrieve → llm_call → translate_output → save_history`.
- **Media agent:** `acquire_audio → transcribe → store → embed`.

**Streaming.** The narrative streams over SSE straight out of the content graph, using LangGraph's `messages` stream mode. Stage events follow as each node finishes.

## Running locally

### Prerequisites

- Python 3.11+ and Node 20+
- `ffmpeg`, needed by yt-dlp and faster-whisper for some formats
- On Linux, `espeak-ng` for text-to-speech
- AWS credentials that can invoke Claude models on Bedrock

### Backend

```bash
cd server
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env        # set AWS credentials/region and Bedrock model ids
uvicorn main:app --reload   # http://localhost:8000 — API docs at /docs, MCP at /mcp
```

The embedding and Whisper models download on first use.

### Frontend

```bash
cd client
npm install                 # also copies MathJax + the pdf.js worker into public/vendor
cp .env.local.example .env.local
npm run dev                 # http://localhost:3000
```

The browser only talks to Next.js. Requests to `/api-backend/*` are proxied to `API_URL` (default `http://localhost:8000`).

### Without AWS credentials

`tests/fake_server.py` serves the real API with a scripted fake LLM and fake embeddings. Use it for UI work:

```bash
cd server && FAKE_TOKEN_DELAY=0.1 python -m tests.fake_server
```

## Tests and checks

```bash
cd server && pytest                         # upload → structure → study (incl. SSE) → game → chat → delete, MCP tools
cd client && npm run type-check && npm run lint && npm run build
```

## API overview

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/books` | Upload a PDF (multipart `file`, optional `toc_pages` like `5-9`) |
| `GET` | `/books`, `/books/{file_id}` | List books, book with chapters/sections |
| `GET` | `/books/{file_id}/sections/{section_id}/pdf` | The section's pages as a PDF |
| `GET`/`POST` | `/books/{file_id}/sections/{section_id}/study` | Cached materials / get-or-generate |
| `POST` | `/books/{file_id}/sections/{section_id}/study/stream` | Same as SSE: `token`, `stage`, `done`, `error` |
| `POST` | `/books/{file_id}/sections/{section_id}/game` | Regenerate the game |
| `GET`/`POST` | `/books/{file_id}/sections/{section_id}/chat` | Chat history / send a message |
| `GET`/`PUT` | `/profile`, `GET /profile/questionnaire` | VARK learning profile |
| `POST` | `/media/youtube`, `/media/lectures`, `/media/presentations` | Transcribe / ingest media |
| | `/collections/...`, `/notes`, `/accessibility/{translate,speech}` | Collections, notes, translation and TTS |

## Known limitations

- **Generated games run as same-origin JavaScript.** This is fine for a single local user. Before multi-user deployment, games should run in a sandboxed iframe.
- **No authentication.** `X-User-Id` is trusted as-is.
- **Image notes aren't OCR'd.** Only PDF notes have their text extracted.
