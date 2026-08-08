"""In-memory ``VectorStore`` stand-in for tests — no real Qdrant. Computes
cosine similarity directly so ``search`` behaves enough like the real
thing to test owner/material scoping and subtree filtering, which is what
these tests actually need to verify.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from bson import ObjectId

from learnai.services.retrieval.vector_store import Chunk, SearchHit


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class _Point:
    owner_id: ObjectId
    material_id: ObjectId
    node_id: str
    node_path: list[str]
    page: int
    title: str
    text: str
    vector: list[float]


@dataclass
class FakeVectorStore:
    points: dict[str, _Point] = field(default_factory=dict)

    async def upsert(
        self, *, owner_id: ObjectId, chunks: list[Chunk], vectors: list[list[float]]
    ) -> None:
        for chunk, vector in zip(chunks, vectors, strict=True):
            key = f"{owner_id}:{chunk.material_id}:{chunk.node_id}:{chunk.chunk_index}"
            self.points[key] = _Point(
                owner_id=owner_id,
                material_id=chunk.material_id,
                node_id=chunk.node_id,
                node_path=chunk.node_path,
                page=chunk.page,
                title=chunk.title,
                text=chunk.text,
                vector=vector,
            )

    async def search(
        self,
        *,
        owner_id: ObjectId,
        query_vector: list[float],
        limit: int = 5,
        material_id: ObjectId | None = None,
        scope_node_id: str | None = None,
    ) -> list[SearchHit]:
        candidates = [
            point
            for point in self.points.values()
            if point.owner_id == owner_id
            and (material_id is None or point.material_id == material_id)
            and (scope_node_id is None or scope_node_id in point.node_path)
        ]
        scored = sorted(candidates, key=lambda p: _cosine(p.vector, query_vector), reverse=True)
        return [
            SearchHit(
                material_id=point.material_id,
                node_id=point.node_id,
                node_path=point.node_path,
                page=point.page,
                title=point.title,
                text=point.text,
                score=_cosine(point.vector, query_vector),
            )
            for point in scored[:limit]
        ]

    async def delete_material(self, *, owner_id: ObjectId, material_id: ObjectId) -> None:
        self.points = {
            key: point
            for key, point in self.points.items()
            if not (point.owner_id == owner_id and point.material_id == material_id)
        }
