"""Embed a query and search — the function the chat agent's
``search_materials`` tool (Phase 6) will call directly. Scoped (a
``scope_node_id`` subtree) when the caller already knows which chapter
the question is about — the common case, per the modernization plan, when
someone is reading and asks about what's in front of them; global
(``scope_node_id=None``) otherwise. Either way ``owner_id`` is required
and always forwarded to ``VectorStore.search`` — there is no unscoped
path here either.
"""

from __future__ import annotations

from bson import ObjectId

from learnai.services.retrieval.embedder import Embedder
from learnai.services.retrieval.vector_store import SearchHit, VectorStore


async def search_materials(
    query: str,
    *,
    owner_id: ObjectId,
    embedder: Embedder,
    vector_store: VectorStore,
    material_id: ObjectId | None = None,
    scope_node_id: str | None = None,
    limit: int = 5,
) -> list[SearchHit]:
    [query_vector] = await embedder.embed([query])
    return await vector_store.search(
        owner_id=owner_id,
        query_vector=query_vector,
        limit=limit,
        material_id=material_id,
        scope_node_id=scope_node_id,
    )
