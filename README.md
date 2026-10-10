# LearnAI

LearnAI turns a textbook PDF into a personalized study experience. For every section of a book it generates, tailored to the learner's VARK learning style:

- **Narrative.** A rewritten explanation that streams in as it is written.
- **Game.** An interactive React mini-game generated for the section, run in a sandboxed iframe.
- **Diagrams.** Mermaid diagrams of the key concepts.
- **Tutor chat.** Chat grounded in the section text plus retrieval over everything the learner has uploaded.

It can also transcribe YouTube videos and recorded lectures and ingest slide decks and notes, and it offers translation and text-to-speech.

Everything runs on your own hardware. The models are served by **vLLM** (or any OpenAI-compatible server) on a GPU host on the local network. **Claude via AWS Bedrock** remains available as an alternative LLM provider.

| Concern | Default (`openai` providers → vLLM) | In-process alternative |
|---|---|---|
| Chat / generation | `LLM_PROVIDER=openai`, e.g. Qwen2.5-VL-7B-Instruct | `bedrock` (Claude) |
| Printed table-of-contents parsing (when a PDF has no outline) | The same vision-capable model | |
| Embeddings / RAG | `/v1/embeddings` (e.g. bge-small) + ChromaDB | `local`: sentence-transformers |
| Speech-to-text | `/v1/audio/transcriptions` (Whisper), audio chunked with ffmpeg | `local`: faster-whisper |
| Translation | The chat model | `argos`: argostranslate |
| Text-to-speech | pyttsx3 (espeak-ng) | |
| PDF text, outline, page rendering | PyMuPDF | |
| Storage | Local filesystem under `DATA_DIR` | |
| Auth | None yet: identity is the `X-User-Id` header (default `default`) | |

The in-process alternatives need the `local-ml` extra (`uv sync --extra local-ml`), which pulls in PyTorch. The default server image leaves them out, so it stays small enough for Raspberry Pi nodes.

## Architecture

```
client/  Next.js 16 (App Router) · React 19 · TypeScript · Tailwind 4 + shadcn/ui · Vercel AI SDK + AI Elements
         · TanStack Query · Zustand
  app/         routes: /home /upload /library /questionnaire /study/[fileId] /study/[fileId]/[sectionId]
               /collections /collections/[id] /media /media/{transcriptions,presentations,notes}/[id]
  api/         typed hooks per backend resource (books, study, chat, profile, media, …)
  components/  ui/ (shadcn/ui) · ai-elements/ (AI Elements: conversation, message, prompt input, …)
               · layout/ · study/ · game/ · upload/ · library/ · collections/ · media/ · shared/
  public/sandbox/  the game frame: a static page + runtime that compiles and renders generated games
  types/       API contracts mirrored from server/models
  store/       UI preferences only (server state lives in TanStack Query)

server/  FastAPI · LangGraph · FastMCP
  routes/      HTTP only: validation, status codes, response models
  agents/      LangGraph workflows: document ingestion, study content, chat, media
  services/    single-purpose operations: books, storage, RAG, media, profile, accessibility
  models/      Pydantic request/response models
  utils/       pure helpers: prompts, TOC normalization, game-code and diagram cleanup, SSE
  core/        config, local storage, vector store, LLM client (vLLM / Bedrock)
  mcp_server/  the same local services exposed as MCP tools, mounted at /mcp
  tests/       offline end-to-end API tests (fake LLM + embeddings)
```

**The study model.**
- **Books and sections.** An uploaded PDF becomes a *book*. Its outline (or the vision model's reading of its printed TOC) is normalized into chapters and *sections*. Each section gets a stable id such as `ch3.s2` and an explicit page range. Sections are the unit of study, and every generated artifact is cached per section.
- **Collections.** Collections group sections, transcripts, slides and notes. A collection has the same study guide, game, diagrams and chat as a section, generated over all of its materials. Every upload also gets a hidden single-item collection, so a lecture or a slide deck can be studied on its own ("Study" on its page). Changing a collection's materials discards its generated study guide; its chat history is kept.

**Agents.**
- **Document agent:** `save_upload → read_outline → (vision TOC) → normalize → save_metadata`. Section text is then indexed in the background.
- **Content agent:** `load_cached → rag → narrative → game_idea → game_code → diagrams → save`. A cache hit short-circuits the run.
- **Game agent.** `game_code` is a LangChain ReAct agent that builds the game as a code artifact with three tools (`agents/game_tools.py`): `write_game` for the first draft, `view_game` to read it with line numbers, and `edit_game` for targeted replacements. Each write saves the artifact with a new `game_version`. The agent's conversation is kept per unit (`game-sessions/`), so it picks up where it left off.
- **Fixing games from the browser.** Games are checked where they run. When a game breaks, at the start or mid-game, the sandbox reports the error, the game code line and the game's stack frames. The client sends them to `/game/fix` automatically (up to 3 times in a row; after that the student can retry). The game graph then enters straight at `game_code`, and the agent continues its conversation with the error as the next message, fixing the game with edits. A report about an older `game_version` gets the current game back. The same graph, entered at `game_idea`, makes a new game.
- **Chat agent:** `load_context → translate_input → tutor → translate_output → save_history`. `tutor` is a LangChain ReAct agent (`create_agent`) with tools in `server/agents/tutor_tools.py`: `search_materials` finds passages and `read_materials` reads a source from an offset. Instead of the section text, its system prompt lists the chat's sources (id, title, length) so it can read them directly. Each tool response is capped in code (search previews share 6,000 characters, a read returns at most 4,000) and says where its text sits and how to read on. The web client streams it through `/chat/stream`, which speaks the [AI SDK UI message stream protocol](https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol), so `useChat` consumes the backend directly. The server keeps the history, so each request carries only the new message.
- **Media agent:** `acquire_audio → transcribe → store → embed`.

**Streaming.** The narrative streams over SSE straight out of the content graph, using LangGraph's `messages` stream mode. Stage events follow as each node finishes.

**Game sandbox.** Generated game code never runs in the app's own page:

- **The frame.** `DynamicGameComponent` renders `public/sandbox/game.html` in an iframe with `sandbox="allow-scripts"` and no `allow-same-origin`. The frame therefore has an opaque origin: it can't read the app's DOM, cookies or storage, call the API, or navigate the page.
- **Running a game.** The frame loads React and MathJax from `public/vendor`. When it posts `ready`, the parent sends the game code with `postMessage`. The frame compiles it with the same contract as before and posts back its content height and the first error the game hits (with the game code line and stack).
- **Headers.** Next.js serves `/sandbox/*` with a CSP that re-applies the sandbox and sets `connect-src 'none'` (no fetch, XHR or WebSocket, and images only from `data:`/`blob:`), so the frame stays isolated even if opened directly. Sandbox scripts are loaded with CORS so game error messages aren't hidden.

## Running locally

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (it installs the Python version pinned in `server/.python-version`, 3.12) and Node 20+
- `ffmpeg`, needed by yt-dlp and for chunking audio sent to a remote Whisper
- On Linux, `espeak-ng` for text-to-speech
- A model server: vLLM (see [deploy/vllm](deploy/vllm/docker-compose.yml)) or another OpenAI-compatible endpoint, or AWS credentials for Claude on Bedrock

### Backend

```bash
cd server
uv sync                     # creates .venv from uv.lock; add --extra local-ml for in-process models
cp .env.example .env        # point OPENAI_BASE_URL / EMBEDDING_BASE_URL / STT_BASE_URL at your model servers
uv run uvicorn main:app --reload   # http://localhost:8000 — API docs at /docs, MCP at /mcp
```

`GET /health/dependencies` reports whether each configured model server is reachable and serves the configured model.

### Frontend

```bash
cd client
npm install                 # also copies MathJax + the pdf.js worker into public/vendor
cp .env.local.example .env.local
npm run dev                 # http://localhost:3000
```

The browser only talks to Next.js. Requests to `/api-backend/*` are proxied to `API_URL` (default `http://localhost:8000`).

### Without a model server

`tests/fake_server.py` serves the real API with a scripted fake LLM and fake embeddings. Use it for UI work:

```bash
cd server && FAKE_TOKEN_DELAY=0.1 uv run python -m tests.fake_server
```

## Deployment

### Images

Both images are multi-arch (`linux/amd64`, `linux/arm64`):

- **Server image:** about 1.2 GB. It contains no PyTorch; add `--build-arg EXTRAS=local-ml` to bundle the in-process models. It runs as uid 10001 with data in `/data`, and its health checks are `/health` (liveness) and `/health/ready` (storage writable).
- **Client image:** about 300 MB. Next.js runs in standalone mode. `API_URL` is read at runtime by the `/api-backend` proxy route, so the same image works in every environment.

### CI/CD: Forgejo → Woodpecker → Argo CD

[`.woodpecker.yaml`](.woodpecker.yaml) does the following:

- **Every push and PR:** runs the server tests and client checks.
- **Default branch and tags:**
  1. Builds both images for amd64 and arm64.
  2. Pushes them to Forgejo's container registry, tagged with the commit SHA and `latest`.
  3. Commits the SHA into `deploy/k8s/kustomization.yaml`, with `[CI SKIP]` in the message so it doesn't trigger another pipeline.
- **Argo CD** ([`deploy/argocd/application.yaml`](deploy/argocd/application.yaml)) watches `deploy/k8s` and rolls the pods out.

One-time setup:

1. **Placeholders:** replace `git.example.lan/OWNER` in `.woodpecker.yaml`, `deploy/k8s/kustomization.yaml` and `deploy/argocd/application.yaml`.
2. **Woodpecker secrets:** add `registry_username`, `registry_password` (a token with `package:write`) and `forgejo_push_token` (a token with `repository:write`).
3. **Woodpecker server:** set `WOODPECKER_PLUGINS_PRIVILEGED=woodpeckerci/plugin-docker-buildx`.
4. **Woodpecker agent (Ryzen):** register QEMU so it can build arm64 images: `docker run --privileged --rm tonistiigi/binfmt --install arm64`. Emulated arm64 builds are slow; registry build caches (`:buildcache`) keep later runs short. A Woodpecker agent on a Pi could build arm64 natively instead.
5. **Cluster secrets** (they stay out of git):
   ```bash
   kubectl create namespace learnai
   kubectl -n learnai create secret docker-registry registry-credentials \
     --docker-server=git.example.lan --docker-username=<user> --docker-password=<token>
   kubectl -n learnai create secret generic learnai-server-secrets --from-env-file=secret.env   # optional
   ```
6. **Register the app with Argo CD:** `kubectl apply -n argocd -f deploy/argocd/application.yaml`. If the repo is private, also add it as a repository in Argo CD.

`.github/workflows/ci.yml` does the same build to GHCR while the repo lives on GitHub. Delete it after the move.

### Model host (vLLM)

[`deploy/vllm/docker-compose.yml`](deploy/vllm/docker-compose.yml) runs one vLLM process per model on the GPU host:

| Port | Model |
|---|---|
| `:8001` | Chat + vision: Qwen2.5-VL-7B-Instruct |
| `:8002` | Embeddings: bge-small-en-v1.5 |
| `:8003` | Whisper large-v3-turbo |

Check the flags against your vLLM version and GPU memory.

Keep `LLM_MAX_OUTPUT_TOKENS` plus the prompt under `--max-model-len`. Source material is clipped to `LLM_MAX_SOURCE_CHARS`, about 4 characters per token.

### k3s (Raspberry Pi cluster)

```bash
# Point the config at the GPU host, and set the hostname
$EDITOR deploy/k8s/server.env          # OPENAI_BASE_URL, EMBEDDING_BASE_URL, STT_BASE_URL, models
$EDITOR deploy/k8s/ingress.yaml
# Argo CD applies deploy/k8s; without Argo: kubectl apply -k deploy/k8s
kubectl -n learnai get pods
kubectl -n learnai exec deploy/learnai-server -- \
  python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/health/dependencies').read().decode())"
```

How the manifests behave:

- **Server:** a single replica with the `Recreate` strategy, because it owns the data volume (files plus embedded Chroma). The 20 Gi PVC uses k3s's `local-path` provisioner by default. Switch to Longhorn or NFS if the pod must be able to move between nodes.
- **Client:** stateless; scale it freely.
- **Ingress:** Traefik routes `/` to the client and `/mcp` to the server.

Generation requests stream or wait for minutes, which Traefik allows by default.

Images need a 64-bit OS on the Pis (arm64).

### Single machine

`docker compose up -d` serves the app at http://localhost:3000 using `server/.env`.

## Tests and checks

```bash
cd server && uv run pytest                  # upload → structure → study (incl. SSE) → game → chat → delete,
                                            # MCP tools, and the vLLM/OpenAI provider path against a fake server
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
| `POST` | `/books/{file_id}/sections/{section_id}/game/fix` | Fix the game after a browser error (`{error, version, line?, phase?, stack?}`) |
| `GET`/`POST` | `/books/{file_id}/sections/{section_id}/chat` | Chat history / send a message |
| `POST` | `/books/{file_id}/sections/{section_id}/chat/stream` | Same, streamed as an AI SDK UI message stream (`{message, language}`) |
| `GET`/`PUT` | `/profile`, `GET /profile/questionnaire` | VARK learning profile |
| `POST` | `/media/youtube` | Start transcribing a video in the background; returns a task to poll |
| `GET` | `/media/tasks/{task_id}` | A background task's stage, progress and, when done, result |
| `POST` | `/media/lectures`, `/media/presentations` | Transcribe / ingest media |
| `GET` | `/media/transcriptions[/{job_id}]`, `/media/presentations[/{id}]` | List media / one transcript or deck |
| `GET`/`POST` | `/notes`, `GET /notes/{notes_id}` | List / upload notes (PDF or image), one note |
| `GET`/`POST` | `/collections` | List (`?include_auto=true` adds per-upload ones) / create `{name, materials}` |
| `GET`/`PATCH`/`DELETE` | `/collections/{id}` | One collection / rename `{name}` / delete |
| `PUT` | `/collections/{id}/materials` | Replace materials |
| | `/collections/{id}/study`, `/study/stream`, `/game`, `/game/fix`, `/chat`, `/chat/stream` | Same as for a section |
| `POST` | `/accessibility/{translate,speech}` | Translation and TTS |

## Known limitations

- **No authentication.** `X-User-Id` is trusted as-is. Keep the ingress on your LAN, or put auth in front of it (e.g. Traefik basic-auth or forward-auth middleware).
- **One server replica.** Storage and the vector index are local to the server pod.
- **Image notes aren't OCR'd.** Only PDF notes have their text extracted.
