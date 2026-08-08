"""Text embedding — FastEmbed (ONNX, no PyTorch pull) wrapping
``settings.embedding_model`` (default ``BAAI/bge-small-en-v1.5``, 384-dim).
Loaded once per process at startup — both the API (to embed a search
query) and the worker (to index a section's chunks right after extracting
it) need this, and model load is expensive enough that it must happen
once, never per call, matching the plan's guidance for Whisper/Piper.

``embed`` is async despite FastEmbed's own API being synchronous: it's a
local ONNX inference call, not I/O, but it's CPU-bound enough (especially
for a batch of chunks) that running it inline would block the event loop
it's called from — so the real adapter pushes it to a thread.

Loading the model is a real fetch (from a local cache once warm, from
HuggingFace on a cold one — see the Kubernetes models initContainer in
the modernization plan) and deliberately deferred to the first ``embed()``
call rather than done in ``__init__``: constructing this once in
``lifespan``/worker startup must never be able to fail process startup
itself, the same reasoning ``main.py`` uses ``ArqRedis.from_url`` (no
eager connection) instead of ``arq.connections.create_pool`` for.
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from fastembed import TextEmbedding


class Embedder(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class FastEmbedEmbedder:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: TextEmbedding | None = None

    async def embed(self, texts: list[str]) -> list[list[float]]:
        def _run() -> list[list[float]]:
            if self._model is None:
                self._model = TextEmbedding(self._model_name)
            return [vector.tolist() for vector in self._model.embed(texts)]

        return await asyncio.to_thread(_run)
