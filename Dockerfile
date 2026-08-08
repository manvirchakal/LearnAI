# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# The api image intentionally excludes the [ml] extra (fastembed, faster-whisper,
# piper-tts) so it stays small and starts fast — those are worker-only. The
# worker image builds on top of the same base with [ml] + [media] + [games]
# added. Two separate `uv sync` targets below produce two separate venvs.
# ---------------------------------------------------------------------------

FROM python:3.11-slim AS base
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock LICENSE.md README.md ./

# --- builder: api -----------------------------------------------------------
FROM base AS builder-api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
COPY src/ src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- builder: worker ---------------------------------------------------------
FROM base AS builder-worker
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra ml --extra media --extra games --no-install-project
COPY src/ src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra ml --extra media --extra games

# --- runtime: api -------------------------------------------------------------
FROM python:3.11-slim AS api
RUN groupadd -r learnai && useradd -r -g learnai learnai
WORKDIR /app
COPY --from=builder-api /app/.venv /app/.venv
COPY --from=builder-api /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
USER learnai
EXPOSE 8000
CMD ["uvicorn", "learnai.main:app", "--host", "0.0.0.0", "--port", "8000"]

# --- runtime: worker -----------------------------------------------------------
# ffmpeg: required by yt-dlp (YouTube audio extraction, Phase 3) and by the
# faster-whisper preprocessing path (Phase 7). Baked in now so this layer
# doesn't need rebuilding when those phases land.
FROM python:3.11-slim AS worker
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r learnai && useradd -r -g learnai learnai
WORKDIR /app
COPY --from=builder-worker /app/.venv /app/.venv
COPY --from=builder-worker /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
USER learnai
CMD ["arq", "learnai.worker.settings.WorkerSettings"]
