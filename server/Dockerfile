# LearnAI API. Multi-arch (linux/amd64, linux/arm64).
#   docker build -t learnai-server server/
#   docker build --build-arg EXTRAS=local-ml ...   # bundle in-process embeddings/Whisper/argos (PyTorch, large)

ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim-bookworm AS build
ARG EXTRAS=""
COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /bin/uv
# Build into /venv with the image's own Python; copy files so /venv is self-contained
ENV UV_PROJECT_ENVIRONMENT=/venv \
    UV_PYTHON=/usr/local/bin/python3 \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /src
# Dependencies first so code changes don't invalidate this layer
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project \
      $(echo "$EXTRAS" | tr ',' '\n' | sed '/^$/d; s/^/--extra /')
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable \
      $(echo "$EXTRAS" | tr ',' '\n' | sed '/^$/d; s/^/--extra /')


FROM python:${PYTHON_VERSION}-slim-bookworm
# ffmpeg: yt-dlp and STT chunking · espeak-ng: text-to-speech
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg espeak-ng libespeak-ng1 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --uid 10001 --create-home --shell /usr/sbin/nologin learnai \
 && mkdir -p /data && chown learnai:learnai /data

COPY --from=build /venv /venv
ENV PATH=/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/data \
    CHROMA_DIR=/data/vectorstore \
    HF_HOME=/data/cache/huggingface \
    XDG_CACHE_HOME=/data/cache \
    ANONYMIZED_TELEMETRY=False

USER learnai
WORKDIR /home/learnai
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=4)"
# One worker: uploads, the vector store and in-process background indexing
# assume a single process owning /data.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
