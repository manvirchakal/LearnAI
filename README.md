# LearnAI

Turn a textbook, a lecture recording, or a YouTube video into study material:
a narrative walkthrough written for how you learn, a playable game built from
the concepts, Mermaid diagrams, and a chat tutor grounded in the source with
citations.

Upload a PDF and the API returns immediately with a job id; a worker reads
the document with Claude's native PDF support, builds a table of contents,
and extracts each section on demand. Group any mix of sections into a
*collection* and generate against it. Audio and video go through the same
pipeline — transcribed locally with faster-whisper, bucketed into
timestamped sections, and from there indistinguishable from a chapter of a
book to everything downstream.

> **Status.** The backend (`src/learnai`) is a ground-up rewrite of the
> original hackathon project and is what this README documents. `client/` is
> the original Create React App frontend, updated to talk to the new API but
> not yet rewritten; `server/` is the superseded original backend, kept only
> until the frontend work lands. Neither is linted or type-checked.

---

## Contents

- [Architecture](#architecture)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [API](#api)
- [Development](#development)
- [Tests](#tests)
- [Security](#security)
- [License](#license)

---

## Architecture

Two processes over four datastores. Nothing runs on a cloud provider's
managed AI services — the whole stack comes up with `docker compose up` and
one Anthropic API key.

```
                    ┌──────────────┐
  browser  ────────▶│  api         │  FastAPI. Serves requests, enqueues jobs.
                    │  (uvicorn)   │  Never blocks on a model call it can defer.
                    └──────┬───────┘
                           │ Redis (ARQ queue)
                    ┌──────▼───────┐
                    │  worker      │  Extraction, transcription, embedding.
                    │  (arq)       │  Owns every heavy/slow operation.
                    └──────┬───────┘
                           │
   ┌───────────┬───────────┼───────────┬────────────┐
   ▼           ▼           ▼           ▼            ▼
 MongoDB     Qdrant      Redis     filesystem    Anthropic
 documents   vectors     queue +   uploads +     extraction +
             (384-d)     limits    generated     generation
                                   audio
```

**Layers.** `routers → services → repositories → db`, in that order and no
other. The boundaries are not a convention — they're
[import-linter](https://import-linter.readthedocs.io/) contracts in
`pyproject.toml`, checked in CI:

| Contract | What it prevents |
| --- | --- |
| Layered architecture | A repository importing a service; a service importing a router |
| Only repositories may talk to MongoDB | A router or service running its own `pymongo` query |
| Services must not depend on the web framework | Business logic that can only be called through HTTP |
| The typed error hierarchy stays framework-free | `errors.py` growing a FastAPI import and becoming unusable in the worker |
| No AWS SDK anywhere | Quiet re-introduction of the Bedrock/S3/Cognito coupling this rewrite removed |

**Services** (`src/learnai/services/`) each hide one external thing behind a
Protocol, so every one of them has a fake in `tests/fakes/`:

- `llm/` — `LLMClient` with `complete`/`structured`/`stream`/`agent`. Two
  implementations: Anthropic, and any OpenAI-compatible endpoint (OpenRouter,
  LM Studio, vLLM, Ollama). Tool use is expressed in backend-neutral
  `AgentTool`/`AgentResult` types so callers never import an SDK's tool
  classes.
- `extraction/` — PDF reading via Claude's native document blocks. Always
  Anthropic, independent of which backend generation uses.
- `ingestion/` — PDF page-range slicing, transcript bucketing, YouTube audio
  download.
- `generation/` — narrative, game idea + code, diagrams, and the esprima AST
  validator that inspects generated JavaScript before it is ever served.
- `retrieval/` — token chunking, FastEmbed embeddings, Qdrant search.
- `agent/` — the chat tutor's tool loop over retrieval.
- `asr.py` / `tts.py` — faster-whisper and Piper, both loaded lazily on first
  call inside `asyncio.to_thread` so a missing model can't fail startup.
- `limits.py` — per-user request rates and daily quotas as Redis counters.

**Repositories** (`src/learnai/repositories/`) all descend from
`ScopedRepository`, which binds `owner_id` at construction and injects it
into every query. There is no unscoped read path to forget to scope. See
[Security](#security).

---

## Quickstart

You need Docker and an Anthropic API key. Nothing else — no cloud account,
no OAuth app, no model downloads to arrange.

```bash
git clone https://github.com/manvirchakal/LearnAI && cd LearnAI
cp .env.example .env          # then set ANTHROPIC_API_KEY
docker compose up -d
curl localhost:8000/health/ready
```

That brings up the API, the worker, MongoDB, Qdrant and Redis. Interactive
API docs are at <http://localhost:8000/docs>.

`DEV_AUTH_BYPASS=true` (the default in `.env.example`) mounts
`POST /auth/dev-login`, so you can use the whole API without configuring
Google OAuth:

```bash
curl -c jar -X POST localhost:8000/auth/dev-login   # signs you in as dev@localhost
curl -b jar -F file=@calculus.pdf localhost:8000/api/v1/materials
```

The upload returns a `job_id`; poll `GET /api/v1/jobs/{job_id}` until it
reports `succeeded`, then `GET /api/v1/materials/{id}/tree`.

The app refuses to start with `DEV_AUTH_BYPASS` on when
`ENVIRONMENT=production` — that's a settings validator, not a convention.

**The frontend** is still Create React App and isn't part of the compose
stack yet (the `client` service sits behind the `full` profile, waiting on
the Vite rewrite). Run it directly:

```bash
cd client
cp .env.example .env.local    # REACT_APP_API_BASE_URL defaults to :8000
npm ci && npm start           # http://localhost:3000
```

`http://localhost:3000` is already in the compose stack's default
`CORS_ORIGINS`, so nothing else needs changing.

---

## Configuration

Every environment variable the app reads is declared, typed, and validated in
`src/learnai/config.py`; nothing is read at import time. `.env.example` is
the annotated copy — below is the shape of it.

| Group | Variables | Notes |
| --- | --- | --- |
| Environment | `ENVIRONMENT` | `development` \| `test` \| `production`. Production runs extra validation (below). |
| Datastores | `MONGODB_URI`, `MONGODB_DB`, `QDRANT_URL`, `REDIS_URL` | Defaults match the compose service names. |
| Storage | `STORAGE_BACKEND`, `STORAGE_ROOT`, `MINIO_*` | `local` writes to a shared volume (a PVC in Kubernetes). `minio` is the escape hatch for clusters with no ReadWriteMany StorageClass. |
| Ingestion LLM | `ANTHROPIC_API_KEY` | Required even in development. PDF reading uses Claude's native document blocks, which have no OpenAI-compatible equivalent. |
| Generation LLM | `LLM_BACKEND`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL_DEFAULT`, `LLM_SUPPORTS_JSON_SCHEMA` | `anthropic` (default, reuses the key above) or `openai_compatible` pointed at any Chat Completions endpoint. |
| Per-task tuning | `LLM_MODEL_OVERRIDES`, `LLM_EFFORT_OVERRIDES`, `LLM_MAX_TOKENS_OVERRIDES` | Keyed by task (`narrative`, `game_code`, `chat`, …) so cost is tunable without touching call sites. |
| Auth | `GOOGLE_CLIENT_ID`, `SESSION_SECRET`, `ACCESS_TOKEN_TTL_SECONDS`, `REFRESH_TOKEN_TTL_SECONDS`, `DEV_AUTH_BYPASS` | Google ID tokens in, our own HS256 session cookies out. |
| HTTP | `CORS_ORIGINS` | A list. No hardcoded origin anywhere. |
| Limits | `RATE_LIMIT_ENABLED`, `RATE_LIMIT_PER_MINUTE`, `GENERATION_QUOTA_PER_DAY`, `INGESTION_QUOTA_PER_DAY` | Off by default locally; mandatory in production. |
| Worker models | `WHISPER_MODEL`, `WHISPER_COMPUTE_TYPE`, `PIPER_VOICE_DIR`, `PIPER_VOICE_MAP`, `EMBEDDING_MODEL`, `EMBEDDING_DIM` | Downloaded on first use into the `models` volume. |
| Retrieval | `CHUNK_TOKENS`, `CHUNK_OVERLAP_TOKENS`, `QDRANT_COLLECTION` | |

With `ENVIRONMENT=production` the settings validator refuses to start the
process unless `DEV_AUTH_BYPASS` is off, `CORS_ORIGINS` is set,
`SESSION_SECRET` is ≥32 characters, `ANTHROPIC_API_KEY` and
`GOOGLE_CLIENT_ID` are present, and `RATE_LIMIT_ENABLED` is on. A
misconfigured production process fails loudly at boot instead of running
open.

---

## API

`GET /docs` has the full generated reference. The shape of it:

| | |
| --- | --- |
| `POST /auth/google` · `/refresh` · `/logout` · `GET /auth/me` | Google ID token in, session cookies out |
| `POST /auth/dev-login` | Only mounted when `DEV_AUTH_BYPASS` is on |
| `GET`/`PUT /api/v1/profile` | Learning-style questionnaire; the description is generated server-side, never client-supplied |
| `POST`/`GET /api/v1/materials` | Upload a PDF (202 + job id), list materials |
| `GET /api/v1/materials/{id}` · `/tree` · `/sections/{node_id}` | Metadata, table of contents, one section's extracted content |
| `POST /api/v1/media/lectures` · `/youtube` | Audio/video upload and YouTube import, both 202 + job id |
| `POST /api/v1/media/translate` · `/tts` | Claude translation (cached by content hash) and Piper speech |
| `POST`/`GET /api/v1/collections`, `GET`/`PUT /api/v1/collections/{id}[/materials]` | Group sections from any materials into one study unit |
| `GET /api/v1/collections/{id}/narrative` · `POST .../game` · `.../diagrams` | Generation, keyed by a fingerprint of the inputs so identical requests reuse the stored artifact |
| `GET`/`POST /api/v1/collections/{id}/chat` | Tutor grounded in the collection, with citations |
| `GET /api/v1/jobs/{id}` | Status for anything that returned 202 |
| `GET /health/live` · `/health/ready` | Liveness never touches a dependency; readiness checks Mongo, Qdrant and Redis |

Errors are RFC 7807 `application/problem+json` throughout, produced from a
typed `AppError` hierarchy in `errors.py`. `429` responses carry
`Retry-After`.

---

## Development

[uv](https://docs.astral.sh/uv/) manages the environment.

```bash
uv sync --all-extras --dev
uv run uvicorn learnai.main:app --reload         # api
uv run arq learnai.worker.settings.WorkerSettings # worker
```

The checks CI runs, in the order it runs them:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/learnai tests
uv run lint-imports            # the architecture contracts
uv run pytest -q
```

`mypy` is strict on `services`, `repositories` and `schemas` — the layers
where a type error is a correctness bug rather than an ergonomic one.

Heavy inference dependencies are optional extras (`ml`, `media`, `games`) so
the API image stays slim; only the worker image installs them.

Schema changes go in `src/learnai/db/migrations/` as a new `mNNNN_*.py`
module added to `ALL_MIGRATIONS`. They're applied at API startup, tracked in
a `migrations` collection, and are idempotent — index creation, mostly.

---

## Tests

Four tiers, by what they're allowed to touch:

| Tier | Count | Touches | Run by default |
| --- | --- | --- | --- |
| `tests/unit` | 256 | Nothing. Fakes for every Protocol. | yes |
| `tests/e2e` | 112 | The real app through `TestClient`; every external faked. | yes |
| `tests/integration` | 13 | Real MongoDB and Qdrant. | no — `-m integration` |
| `tests/contract` | 7 | The real Anthropic API. Costs money. | no — `-m live` |

```bash
uv run pytest -q                           # the 368 that need nothing running
uv run pytest -m integration               # needs docker compose up -d mongo qdrant
uv run pytest -m live                      # needs ANTHROPIC_API_KEY
cd client && CI=true npm test -- --watchAll=false
```

Coverage is gated at 90% (`fail_under` in `pyproject.toml`, applied by
pytest-cov on any `--cov` run, local or CI). Currently 96% overall — 94% on
services, 99% on repositories, 98% on routers.

Two of the e2e suites are inventories rather than feature tests, and exist so
that *forgetting* fails:

- `test_auth_matrix.py` — every route, unauthenticated.
- `test_idor_matrix.py` — every `{id}` route, probed with another user's id.

---

## Security

The rewrite's security posture, and where each piece is enforced:

**Tenant isolation.** `ScopedRepository` (`repositories/base.py`) takes
`owner_id` at construction and merges it into every filter. A missing
document and another user's document both produce **404, never 403** — a 403
would confirm the resource exists. `tests/e2e/test_idor_matrix.py` probes
every `{id}` route to keep it that way.

**Generated code.** LLM-written game JavaScript runs in an iframe with
`sandbox="allow-scripts"` and deliberately *without* `allow-same-origin`, so
it has an opaque origin: no cookies, no `localStorage`, no parent DOM, no
same-origin fetch. The shell document's own CSP is `default-src 'none'`, and
the code is embedded as a JSON string rather than spliced into the shell's
source. `services/generation/game_validator.py` walks the parsed AST as
defence in depth behind that, not in place of it.
`client/src/components/GameFrame.test.js` is a regression test for the
sandbox attributes specifically.

**Uploads.** Content types are allow-listed, stored paths are generated
server-side, and `services/storage/local.py` resolves every path and refuses
anything that escapes the storage root — including via symlink.

**Auth.** Google ID tokens are verified server-side (JWKS fetched and cached
by `google-auth`, never at import time). Sessions are HS256 tokens in
`HttpOnly`/`SameSite=Lax` cookies. Refresh tokens rotate on every use and are
stored server-side keyed by a `family_id`; presenting an already-redeemed one
means it was replayed, so the entire family is revoked rather than just that
token.

**Abuse.** Per-user request rates and daily generation/ingestion quotas are
fixed-window Redis counters (`services/limits.py`). They fail *open* — Redis
being down degrades to unlimited rather than to an outage — and are required
in production by the settings validator.

**Dependencies.** `pip-audit` runs in CI over the locked runtime closure and
is a hard gate. The client's `npm audit` is reported but not gated; the
remaining advisories all sit behind major bumps of `react-scripts`,
`react-pdf-highlighter` and `react-router-dom`, and the CI job says so.

---

## License

MIT, with the third-party terms noted in [LICENSE.md](LICENSE.md) — Claude
usage is governed by the [Anthropic API terms](https://www.anthropic.com/legal/terms).
