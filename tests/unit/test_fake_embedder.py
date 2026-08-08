from __future__ import annotations

from tests.fakes.embedder import FakeEmbedder


async def test_embed_is_deterministic_and_dimension_matches() -> None:
    embedder = FakeEmbedder(dim=8)

    first = await embedder.embed(["hello"])
    second = await embedder.embed(["hello"])

    assert first == second
    assert len(first[0]) == 8


async def test_different_text_produces_different_vector() -> None:
    embedder = FakeEmbedder()

    [a], [b] = await embedder.embed(["hello"]), await embedder.embed(["goodbye"])

    assert a != b


async def test_records_calls() -> None:
    embedder = FakeEmbedder()

    await embedder.embed(["a", "b"])

    assert embedder.calls == [["a", "b"]]
