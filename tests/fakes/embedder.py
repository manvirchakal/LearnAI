"""In-memory ``Embedder`` stand-in for tests — deterministic, content-
dependent vectors with no real model load (this sandbox's unit-test tier
has no network access to fetch FastEmbed's ONNX model from HuggingFace;
see ``tests/integration/`` for the real adapter against a real Qdrant).
"""

from __future__ import annotations

import hashlib


class FakeEmbedder:
    def __init__(self, dim: int = 8) -> None:
        self.dim = dim
        self.calls: list[list[str]] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [b / 255 for b in digest[: self.dim]]
