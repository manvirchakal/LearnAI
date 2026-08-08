"""VectorStore and retrieval against a real Qdrant and a real FastEmbed
model — the properties only the real stack can confirm: that owner/subtree
filters actually get enforced by Qdrant's query engine, and that the
"scope to a subtree" retrieval design the modernization plan calls for
actually earns its keep on real embeddings, not just plumbing that
happens to type-check.

Connects to ``settings.qdrant_url`` — the same env var the app itself
reads — using a per-test collection name, dropped after each test. Like
``tests/integration/test_migrations_and_scoped_repository.py``, this is
deliberately not testcontainers-managed: CI's ``test`` job already
provisions a Qdrant ``services:`` container reachable at that URL, and
``docker compose up -d qdrant`` gives the same thing locally.

Building the real ``FastEmbedEmbedder`` here downloads its ONNX model
from HuggingFace on a cold cache — real network access, unlike everything
else in this suite. CI's runners have it; a fully offline dev sandbox may
not, which is a second, independent reason (besides no reachable Qdrant)
this file is ``integration``-marked and excluded from the default run.

Marked ``integration`` (see pyproject.toml) and excluded from the default
``pytest`` invocation (`not live and not integration`) — run explicitly
with `pytest -m integration` once Qdrant is up.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import TypedDict

import pytest
from bson import ObjectId
from qdrant_client import AsyncQdrantClient

from learnai.config import get_settings
from learnai.schemas.documents import SectionContent, TreeNode
from learnai.services.retrieval.chunker import chunk_section
from learnai.services.retrieval.embedder import FastEmbedEmbedder
from learnai.services.retrieval.retriever import search_materials
from learnai.services.retrieval.vector_store import Chunk, QdrantVectorStore, ensure_collection

pytestmark = pytest.mark.integration

_EMBEDDING_DIM = 384  # matches settings.embedding_dim's default (BAAI/bge-small-en-v1.5)


@pytest.fixture
async def client() -> AsyncIterator[AsyncQdrantClient]:
    qdrant = AsyncQdrantClient(url=get_settings().qdrant_url, timeout=30)
    yield qdrant
    await qdrant.close()


@pytest.fixture
async def store(client: AsyncQdrantClient) -> AsyncIterator[QdrantVectorStore]:
    collection = f"test_chunks_{uuid.uuid4().hex[:8]}"
    await ensure_collection(client, name=collection, vector_size=_EMBEDDING_DIM)
    yield QdrantVectorStore(client, collection_name=collection)
    await client.delete_collection(collection)


@pytest.fixture(scope="module")
def embedder() -> FastEmbedEmbedder:
    return FastEmbedEmbedder("BAAI/bge-small-en-v1.5")


async def test_upsert_then_search_returns_the_matching_chunk(
    store: QdrantVectorStore, embedder: FastEmbedEmbedder
) -> None:
    owner, material_id = ObjectId(), ObjectId()
    node = TreeNode(node_id="1", title="Limits", start_page=1, end_page=5)
    section = SectionContent(
        node_id="1",
        text="The limit of a function describes the value it approaches near a point.",
    )
    chunks = chunk_section(
        section,
        material_id=material_id,
        node=node,
        node_path=["1"],
        chunk_tokens=512,
        chunk_overlap_tokens=64,
    )
    vectors = await embedder.embed([c.text for c in chunks])
    await store.upsert(owner_id=owner, chunks=chunks, vectors=vectors)

    hits = await search_materials(
        "what does a limit describe", owner_id=owner, embedder=embedder, vector_store=store
    )

    assert hits
    assert hits[0].node_id == "1"
    assert hits[0].material_id == material_id


async def test_search_never_crosses_owners(
    store: QdrantVectorStore, embedder: FastEmbedEmbedder
) -> None:
    owner_a, owner_b = ObjectId(), ObjectId()
    material_id = ObjectId()
    node = TreeNode(node_id="1", title="Limits", start_page=1, end_page=5)
    section = SectionContent(node_id="1", text="Only owner A should ever see this passage.")
    chunks = chunk_section(
        section,
        material_id=material_id,
        node=node,
        node_path=["1"],
        chunk_tokens=512,
        chunk_overlap_tokens=64,
    )
    vectors = await embedder.embed([c.text for c in chunks])
    await store.upsert(owner_id=owner_a, chunks=chunks, vectors=vectors)

    hits = await search_materials(
        "this passage", owner_id=owner_b, embedder=embedder, vector_store=store
    )

    assert hits == []


async def test_scope_node_id_filters_to_subtree(
    store: QdrantVectorStore, embedder: FastEmbedEmbedder
) -> None:
    owner, material_id = ObjectId(), ObjectId()
    chapter_1 = TreeNode(node_id="1", title="Chapter 1", start_page=1, end_page=5)
    chapter_2 = TreeNode(node_id="2", title="Chapter 2", start_page=6, end_page=10)
    for node, text in (
        (chapter_1, "Content that only lives in chapter one."),
        (chapter_2, "Content that only lives in chapter two."),
    ):
        section = SectionContent(node_id=node.node_id, text=text)
        chunks = chunk_section(
            section,
            material_id=material_id,
            node=node,
            node_path=[node.node_id],
            chunk_tokens=512,
            chunk_overlap_tokens=64,
        )
        vectors = await embedder.embed([c.text for c in chunks])
        await store.upsert(owner_id=owner, chunks=chunks, vectors=vectors)

    hits = await search_materials(
        "chapter content",
        owner_id=owner,
        embedder=embedder,
        vector_store=store,
        scope_node_id="1",
    )

    assert hits
    assert all(hit.node_id == "1" for hit in hits)


async def test_delete_material_removes_only_that_materials_points(
    store: QdrantVectorStore, embedder: FastEmbedEmbedder
) -> None:
    owner = ObjectId()
    material_a, material_b = ObjectId(), ObjectId()
    node = TreeNode(node_id="1", title="Chapter 1", start_page=1, end_page=5)
    for material_id, text in (
        (material_a, "Material A's only passage."),
        (material_b, "Material B's only passage."),
    ):
        section = SectionContent(node_id="1", text=text)
        chunks = chunk_section(
            section,
            material_id=material_id,
            node=node,
            node_path=["1"],
            chunk_tokens=512,
            chunk_overlap_tokens=64,
        )
        vectors = await embedder.embed([c.text for c in chunks])
        await store.upsert(owner_id=owner, chunks=chunks, vectors=vectors)

    await store.delete_material(owner_id=owner, material_id=material_a)

    hits = await search_materials(
        "passage", owner_id=owner, embedder=embedder, vector_store=store, limit=10
    )
    assert all(hit.material_id == material_b for hit in hits)


# --- Retrieval quality: does subtree scoping actually earn its keep? -------
#
# Five pairs of genuinely confusable sibling concepts (limits/continuity,
# Type I/Type II error, mean/median, permutations/combinations, row/column
# vectors) — real conceptual closeness a real embedding model can plausibly
# rank near each other, not contrived string overlap. Each chapter also gets
# a shared boilerplate sentence as generic cross-chapter noise. 20 hand-
# written question/expected-answer pairs total (2 per chapter).

_BOILERPLATE = (
    "This chapter reviews foundational material from earlier lessons and "
    "provides worked examples for further practice."
)


class _Chapter(TypedDict):
    node_id: str
    title: str
    qa: list[tuple[str, str]]


_FIXTURE_CHAPTERS: list[_Chapter] = [
    {
        "node_id": "1",
        "title": "Limits",
        "qa": [
            (
                "What value does a function approach as its input nears a specific point?",
                "The limit of a function describes the value it approaches as the input "
                "gets closer and closer to a particular point.",
            ),
            (
                "What is the formal epsilon-delta definition used for?",
                "The epsilon-delta definition gives a rigorous way to state that a "
                "function's limit at a point equals a specific value.",
            ),
        ],
    },
    {
        "node_id": "2",
        "title": "Continuity",
        "qa": [
            (
                "What three conditions must hold for a function to be continuous at a point?",
                "A function is continuous at a point when it is defined there, has a "
                "limit there, and that limit equals the function's value.",
            ),
            (
                "What kind of break in a graph indicates a discontinuity?",
                "A jump, hole, or asymptote in a function's graph at a point indicates "
                "the function is discontinuous there.",
            ),
        ],
    },
    {
        "node_id": "3",
        "title": "Type I Error",
        "qa": [
            (
                "What happens when a true null hypothesis is incorrectly rejected?",
                "A Type I error occurs when a researcher rejects a null hypothesis that "
                "is actually true, a false positive.",
            ),
            (
                "What symbol represents the Type I error rate?",
                "The significance level, denoted alpha, is the probability of "
                "committing a Type I error in a hypothesis test.",
            ),
        ],
    },
    {
        "node_id": "4",
        "title": "Type II Error",
        "qa": [
            (
                "What happens when a false null hypothesis is not rejected?",
                "A Type II error occurs when a researcher fails to reject a null "
                "hypothesis that is actually false, a false negative.",
            ),
            (
                "What is the statistical power of a test related to?",
                "Statistical power is the probability of correctly rejecting a false "
                "null hypothesis, equal to one minus the Type II error rate.",
            ),
        ],
    },
    {
        "node_id": "5",
        "title": "Mean",
        "qa": [
            (
                "How do you calculate the average of a data set?",
                "The mean is calculated by summing all the values in a data set and "
                "dividing by the number of values.",
            ),
            (
                "Why can outliers distort this measure of central tendency?",
                "Because the mean incorporates every value, a single extreme outlier "
                "can pull it significantly higher or lower.",
            ),
        ],
    },
    {
        "node_id": "6",
        "title": "Median",
        "qa": [
            (
                "How do you find the middle value of a sorted data set?",
                "The median is the middle value of a data set when all values are "
                "arranged in ascending order.",
            ),
            (
                "Why is this measure more resistant to extreme values?",
                "Because the median depends only on the middle position, extreme "
                "outliers barely affect its value.",
            ),
        ],
    },
    {
        "node_id": "7",
        "title": "Permutations",
        "qa": [
            (
                "Does the order of items matter when counting these arrangements?",
                "A permutation counts the number of ways to arrange items where the "
                "order of selection matters.",
            ),
            (
                "What is the formula for arranging r items from a set of n?",
                "The number of permutations of r items chosen from n is n factorial "
                "divided by (n minus r) factorial.",
            ),
        ],
    },
    {
        "node_id": "8",
        "title": "Combinations",
        "qa": [
            (
                "When counting groups of items, does order matter?",
                "A combination counts the number of ways to choose items from a set "
                "where the order of selection does not matter.",
            ),
            (
                "How does the combination formula relate to permutations?",
                "The number of combinations of r items from n equals the number of "
                "permutations divided by r factorial.",
            ),
        ],
    },
    {
        "node_id": "9",
        "title": "Row Vectors",
        "qa": [
            (
                "How are the components of this kind of vector arranged?",
                "A row vector arranges its components horizontally in a single row of a matrix.",
            ),
            (
                "What do you get when you transpose this kind of vector?",
                "Transposing a row vector converts it into a column vector with the "
                "same components.",
            ),
        ],
    },
    {
        "node_id": "10",
        "title": "Column Vectors",
        "qa": [
            (
                "How are the components of this kind of vector arranged vertically?",
                "A column vector arranges its components vertically in a single column "
                "of a matrix.",
            ),
            (
                "What do you get when you transpose this kind of vector?",
                "Transposing a column vector converts it into a row vector with the "
                "same components.",
            ),
        ],
    },
]


@pytest.fixture
async def fixture_textbook(
    store: QdrantVectorStore, embedder: FastEmbedEmbedder
) -> tuple[ObjectId, ObjectId]:
    owner, material_id = ObjectId(), ObjectId()
    for chapter in _FIXTURE_CHAPTERS:
        node_id = chapter["node_id"]
        node = TreeNode(node_id=node_id, title=chapter["title"], start_page=1, end_page=1)
        texts = [_BOILERPLATE] + [answer for _, answer in chapter["qa"]]
        chunks = [
            Chunk(
                material_id=material_id,
                node_id=node_id,
                node_path=[node_id],
                chunk_index=i,
                page=1,
                title=node.title,
                text=text,
            )
            for i, text in enumerate(texts)
        ]
        vectors = await embedder.embed([c.text for c in chunks])
        await store.upsert(owner_id=owner, chunks=chunks, vectors=vectors)
    return owner, material_id


async def test_subtree_scoped_search_beats_unscoped_on_recall_at_3(
    store: QdrantVectorStore,
    embedder: FastEmbedEmbedder,
    fixture_textbook: tuple[ObjectId, ObjectId],
) -> None:
    owner, _material_id = fixture_textbook

    scoped_hits = unscoped_hits = total = 0
    for chapter in _FIXTURE_CHAPTERS:
        node_id = chapter["node_id"]
        for question, answer in chapter["qa"]:
            total += 1

            scoped = await search_materials(
                question,
                owner_id=owner,
                embedder=embedder,
                vector_store=store,
                scope_node_id=node_id,
                limit=3,
            )
            if any(hit.text == answer for hit in scoped):
                scoped_hits += 1

            unscoped = await search_materials(
                question, owner_id=owner, embedder=embedder, vector_store=store, limit=3
            )
            if any(hit.text == answer for hit in unscoped):
                unscoped_hits += 1

    scoped_recall = scoped_hits / total
    unscoped_recall = unscoped_hits / total

    # Scoped search only ever competes against its own chapter's 3 chunks,
    # so it should find the right one almost every time; unscoped competes
    # against all 30 chunks across 10 chapters, five of them genuinely
    # confusable sibling topics — that's where recall should suffer.
    assert scoped_recall > unscoped_recall
    assert scoped_recall >= 0.8
