# Modernization plan — remaining phases

This project is a ground-up rewrite of the original hackathon codebase,
carried out in phases. Phases 0–8 are done and on
`claude/hackathon-project-analysis-k5vyy0`; what follows is the plan for the
two that remain.

> **Why this file exists.** The original plan lived in an agent scratch
> directory that did not survive a container rebuild, so the remaining phases
> were reconstructed from the repository itself — the commit history, the
> forward-references earlier phases deliberately left in comments
> (`pyproject.toml:87`, `docker-compose.yml:74`, `client/src/api/client.js:6`,
> `client/.env.example`), and a fresh audit of `client/`. It lives in the repo
> this time.

---

## Completed (0–8)

| Phase | Outcome |
| --- | --- |
| 0 | Modular backend scaffold, uv tooling, ruff/mypy/import-linter, CI |
| 1 | `ScopedRepository`, Mongo migrations, Google auth + sessions, storage backend |
| 2 | Provider-agnostic `LLMClient` (Anthropic + any OpenAI-compatible endpoint) |
| 3 | PDF ingestion via Claude native document blocks; ARQ worker; jobs API |
| 4 | Tree-aware chunking, FastEmbed embeddings, Qdrant retrieval |
| 5 | Narrative / game / diagram generation, AST validator, sandboxed game iframe |
| 6 | Chat tutor — `agent()` on `LLMClient`, 7 owner-scoped tools, citations |
| 7 | Media — faster-whisper ASR, Piper TTS, YouTube import, cached translation |
| 8 | Rate limits + daily quotas, IDOR matrix, coverage gate, pip-audit, README |

State at the end of Phase 8: 368 tests passing, 95.82% coverage against a 90%
gate, ruff/mypy clean, 5/5 architecture contracts kept.

---

## Phase 9 — Frontend

**Goal.** Get `client/` off Create React App and onto Vite, with a real test
tier, and make it a first-class part of the compose stack and CI rather than
something you run by hand.

**Why now.** Every remaining item is blocked on this. `react-scripts` is
unmaintained and is the root of most of the client's npm advisories; its jest
setup cannot even load `axios` 1.x (ESM), which is why the client has exactly
one test today; and the compose `client` service (profile `full`) references
a `client/Dockerfile` that does not exist, so the documented full-stack
bring-up does not work.

### What the audit found

- **3405 LOC** across 40 files in `client/src`.
- **Only 11 of 26 declared dependencies are actually imported.** Unused:
  `ajv`, `jsx-runtime`, `lucide-react`, `prismjs`, `react-markdown`,
  `react-pdf`, `react-pdf-highlighter`, `react-webcam`, `rehype-raw`,
  `remark-gfm`, `web-vitals`, `@testing-library/user-event`. This matters
  beyond tidiness: `react-pdf-highlighter` is the root of the
  `pdfjs-dist` and `canvas → node-pre-gyp → tar` advisory chains documented
  in `.github/workflows/ci.yml`, and `react-scripts` is the root of the
  `webpack-dev-server` / `svgo` / `nth-check` chain. Dropping code that was
  already dead should clear most of the 35 remaining advisories.
- **Four dead modules**, imported by nothing: `pages/Body.js`,
  `components/Sidebar.js`, `components/ErrorBoundary.js`,
  `reportWebVitals.js`. Plus `public/mathjax-config.html`, unreferenced.
- **`react-router-dom` v6 → v7** is the one dependency bump needing real
  review. Only `BrowserRouter`, `Routes`, `Route`, `Link`, `useNavigate`,
  `useParams` and `useLocation` are used, all unchanged in v7 — so this
  should be a version bump, but it gets verified, not assumed.
- **Two `process.env.REACT_APP_*` reads** — `api/client.js:11` and
  `App.js:35` — both already flagged in comments as moving to
  `import.meta.env.VITE_*` with this migration.

### Steps

1. **Vite build.** Add `vite.config.js` and `@vitejs/plugin-react`; move
   `public/index.html` to the project root and drop the `%PUBLIC_URL%`
   placeholders; rename the 17 files containing JSX from `.js` to `.jsx`
   (esbuild will not parse JSX in `.js`); replace the `react-scripts`
   scripts with `vite` / `vite build` / `vite preview`. Dev server on 5173,
   which `CORS_ORIGINS` and the compose file already anticipate.
2. **Environment variables.** `REACT_APP_API_BASE_URL` →
   `VITE_API_BASE_URL`, `REACT_APP_GOOGLE_CLIENT_ID` →
   `VITE_GOOGLE_CLIENT_ID`, in both call sites, `client/.env.example`, and
   the compose `client` service (which already says `VITE_API_BASE_URL`).
   Remove the now-stale comments that promised this move.
3. **Dependency cleanup.** Drop the 12 unused packages and `react-scripts`;
   bump `react-router-dom` to v7. Re-run `npm audit` and record the real
   number.
4. **Vitest + MSW.** Port `GameFrame.test.js` unchanged in substance — it is
   a security regression test and its assertions must survive the migration
   intact. Add MSW so component tests can exercise real request paths, and
   cover what is currently untested and worth testing: the `api/client.js`
   401-refresh interceptor (including that it does not loop on a failed
   refresh), `AuthContext`, and the `Study` page's tab behaviour.
5. **Dead code.** Delete the four unused modules, their CSS, and
   `mathjax-config.html`.
6. **`client/Dockerfile`.** Multi-stage: `vite build`, then serve the static
   output. Drop the `full` profile from the compose `client` service so
   `docker compose up` brings up the whole stack, and update the README
   quickstart, which currently tells people to run the client by hand.
7. **CI.** Point the `client` job at vite/vitest. If `npm audit` comes back
   clean after step 3, promote it from reported to gated, matching
   `pip-audit`.

**Exit criteria.** `docker compose up` serves a working frontend;
`npm run build` and `npm test` pass in CI; the GameFrame sandbox assertions
still pass; no `react-scripts` anywhere; the client's advisory count is
stated accurately in CI and the README.

**Risk.** MUI v6 + emotion under Vite, and `better-react-mathjax` and
`mermaid` (both of which touch the DOM directly) are the likely friction
points. Each screen gets loaded in a browser before the phase is called done
— a passing build is not evidence that the app renders.

---

## Phase 10 — Delete the old code

**Goal.** Remove the superseded hackathon implementation now that nothing
depends on it.

1. Delete `server/` (`main.py` is 3060 lines and is fully superseded by
   `src/learnai`). Delete the root `requirements.txt`, which `pyproject.toml`
   and `uv.lock` replaced in Phase 0.
2. Remove the `extend-exclude = ["server", "client"]` from the ruff config
   (`pyproject.toml:87`) — the comment there names this phase — and add
   linting for the client instead.
3. Sweep the forward-references the earlier phases left behind: any comment
   still saying "in a later phase" should either be true or be gone.
   `.gitignore` should pick up `.DS_Store`.
4. Decide `_build_storage`'s `minio` branch, which still raises
   `NotImplementedError` (`main.py:62`): implement it or remove the config
   surface that advertises it. Leaving a documented option that fails at
   startup is the worst of the three.

**Exit criteria.** No file in the repo is unreachable from `src/learnai`,
`tests/`, `client/src` or the deployment config; every remaining
forward-reference in a comment is accurate.
