from __future__ import annotations

from bson import ObjectId

from learnai.services.retrieval.retriever import search_materials
from learnai.services.retrieval.vector_store import Chunk
from tests.fakes.embedder import FakeEmbedder
from tests.fakes.vector_store import FakeVectorStore


async def _seeded_store(owner: ObjectId, material_id: ObjectId) -> FakeVectorStore:
    store = FakeVectorStore()
    embedder = FakeEmbedder()
    chunks = [
        Chunk(
            material_id=material_id,
            node_id="1",
            node_path=["1"],
            chunk_index=0,
            page=1,
            title="Chapter 1",
            text="derivatives and limits",
        ),
        Chunk(
            material_id=material_id,
            node_id="2",
            node_path=["2"],
            chunk_index=0,
            page=20,
            title="Chapter 2",
            text="integration by parts",
        ),
    ]
    vectors = await embedder.embed([c.text for c in chunks])
    await store.upsert(owner_id=owner, chunks=chunks, vectors=vectors)
    return store


async def test_search_materials_embeds_query_and_returns_hits() -> None:
    owner, material_id = ObjectId(), ObjectId()
    store = await _seeded_store(owner, material_id)
    embedder = FakeEmbedder()

    hits = await search_materials(
        "derivatives", owner_id=owner, embedder=embedder, vector_store=store
    )

    assert len(hits) == 2
    assert embedder.calls == [["derivatives"]]


async def test_search_materials_scope_node_id_filters_to_subtree() -> None:
    owner, material_id = ObjectId(), ObjectId()
    store = await _seeded_store(owner, material_id)
    embedder = FakeEmbedder()

    hits = await search_materials(
        "anything",
        owner_id=owner,
        embedder=embedder,
        vector_store=store,
        scope_node_id="2",
    )

    assert [h.node_id for h in hits] == ["2"]


async def test_search_materials_never_crosses_owners() -> None:
    owner_a, owner_b = ObjectId(), ObjectId()
    material_id = ObjectId()
    store = await _seeded_store(owner_a, material_id)
    embedder = FakeEmbedder()

    hits = await search_materials(
        "derivatives", owner_id=owner_b, embedder=embedder, vector_store=store
    )

    assert hits == []
