"""Vector search over indexed section chunks — Qdrant, tree-scoped.

Every point carries its ancestry (``node_path``) alongside ``owner_id``/
``material_id``, so a subtree search is a payload filter rather than a
separate index (see the modernization plan's "Retrieval: tree-scoped
vector search"). ``owner_id`` is a required argument on every method here
and is always emitted as a filter — there is no method that can reach
another owner's vectors, the same guarantee ``ScopedRepository`` gives
Mongo.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

from bson import ObjectId
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    VectorParams,
)

# Deterministic namespace for chunk point ids (see _point_id) — re-indexing
# the same (owner, material, node, chunk) overwrites in place rather than
# accumulating duplicates, the same idempotency SectionRepository.upsert
# gives Mongo.
_POINT_ID_NAMESPACE = uuid.UUID("6f5a6e2e-6b8f-4b0a-9a1e-3f9a9f2c9c1a")


@dataclass(frozen=True, slots=True)
class Chunk:
    material_id: ObjectId
    node_id: str
    node_path: list[str]
    chunk_index: int
    page: int
    title: str
    text: str


@dataclass(frozen=True, slots=True)
class SearchHit:
    material_id: ObjectId
    node_id: str
    node_path: list[str]
    page: int
    title: str
    text: str
    score: float


class VectorStore(Protocol):
    async def upsert(
        self, *, owner_id: ObjectId, chunks: list[Chunk], vectors: list[list[float]]
    ) -> None: ...

    async def search(
        self,
        *,
        owner_id: ObjectId,
        query_vector: list[float],
        limit: int = 5,
        material_id: ObjectId | None = None,
        scope_node_id: str | None = None,
    ) -> list[SearchHit]: ...

    async def delete_material(self, *, owner_id: ObjectId, material_id: ObjectId) -> None: ...


def _point_id(owner_id: ObjectId, chunk: Chunk) -> str:
    key = f"{owner_id}:{chunk.material_id}:{chunk.node_id}:{chunk.chunk_index}"
    return str(uuid.uuid5(_POINT_ID_NAMESPACE, key))


async def ensure_collection(client: AsyncQdrantClient, *, name: str, vector_size: int) -> None:
    if not await client.collection_exists(name):
        await client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


class QdrantVectorStore:
    def __init__(self, client: AsyncQdrantClient, *, collection_name: str) -> None:
        self._client = client
        self._collection = collection_name

    async def upsert(
        self, *, owner_id: ObjectId, chunks: list[Chunk], vectors: list[list[float]]
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must be the same length")
        points = [
            PointStruct(
                id=_point_id(owner_id, chunk),
                vector=vector,
                payload={
                    "owner_id": str(owner_id),
                    "material_id": str(chunk.material_id),
                    "node_id": chunk.node_id,
                    "node_path": chunk.node_path,
                    "page": chunk.page,
                    "title": chunk.title,
                    "text": chunk.text,
                },
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        await self._client.upsert(collection_name=self._collection, points=points)

    async def search(
        self,
        *,
        owner_id: ObjectId,
        query_vector: list[float],
        limit: int = 5,
        material_id: ObjectId | None = None,
        scope_node_id: str | None = None,
    ) -> list[SearchHit]:
        must: list[FieldCondition] = [
            FieldCondition(key="owner_id", match=MatchValue(value=str(owner_id)))
        ]
        if material_id is not None:
            must.append(FieldCondition(key="material_id", match=MatchValue(value=str(material_id))))
        if scope_node_id is not None:
            must.append(FieldCondition(key="node_path", match=MatchAny(any=[scope_node_id])))

        response = await self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            query_filter=Filter(must=must),
            limit=limit,
        )
        return [
            SearchHit(
                material_id=ObjectId(point.payload["material_id"]),
                node_id=point.payload["node_id"],
                node_path=point.payload["node_path"],
                page=point.payload["page"],
                title=point.payload["title"],
                text=point.payload["text"],
                score=point.score,
            )
            for point in response.points
            if point.payload is not None
        ]

    async def delete_material(self, *, owner_id: ObjectId, material_id: ObjectId) -> None:
        await self._client.delete(
            collection_name=self._collection,
            points_selector=Filter(
                must=[
                    FieldCondition(key="owner_id", match=MatchValue(value=str(owner_id))),
                    FieldCondition(key="material_id", match=MatchValue(value=str(material_id))),
                ]
            ),
        )
