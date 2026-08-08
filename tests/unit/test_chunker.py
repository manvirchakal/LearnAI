from __future__ import annotations

from bson import ObjectId

from learnai.schemas.documents import SectionContent, TreeNode
from learnai.services.retrieval.chunker import chunk_section, chunk_text


def test_chunk_text_of_empty_string_is_empty() -> None:
    assert chunk_text("", chunk_size=10, overlap=2) == []


def test_chunk_text_shorter_than_chunk_size_is_one_chunk() -> None:
    text = "one two three"
    assert chunk_text(text, chunk_size=10, overlap=2) == [text]


def test_chunk_text_splits_into_overlapping_windows() -> None:
    words = [f"w{i}" for i in range(25)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_size=10, overlap=3)

    assert chunks[0] == " ".join(words[0:10])
    assert chunks[1] == " ".join(words[7:17])
    assert chunks[2] == " ".join(words[14:24])
    assert chunks[3] == " ".join(words[21:25])


def test_chunk_text_last_chunk_never_duplicated() -> None:
    # 21 words, chunk_size=10, overlap=3 -> step 7: starts at 0, 7, 14 (covers
    # to word 24 > 21, so this is the last chunk) — must not also emit a
    # trailing start=21 chunk that duplicates the tail.
    words = [f"w{i}" for i in range(21)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_size=10, overlap=3)

    assert len(chunks) == 3
    assert chunks[-1] == " ".join(words[14:21])


def test_chunk_section_stamps_material_node_and_page() -> None:
    material_id = ObjectId()
    node = TreeNode(node_id="1.1", title="Limits", start_page=5, end_page=9)
    section = SectionContent(node_id="1.1", text=" ".join(f"w{i}" for i in range(15)))

    chunks = chunk_section(
        section,
        material_id=material_id,
        node=node,
        node_path=["1", "1.1"],
        chunk_tokens=10,
        chunk_overlap_tokens=3,
    )

    assert len(chunks) == 2
    for i, chunk in enumerate(chunks):
        assert chunk.material_id == material_id
        assert chunk.node_id == "1.1"
        assert chunk.node_path == ["1", "1.1"]
        assert chunk.page == 5
        assert chunk.title == "Limits"
        assert chunk.chunk_index == i


def test_chunk_section_of_empty_text_is_empty() -> None:
    node = TreeNode(node_id="1.1", title="Limits", start_page=5, end_page=9)
    section = SectionContent(node_id="1.1", text="")

    chunks = chunk_section(
        section,
        material_id=ObjectId(),
        node=node,
        node_path=["1.1"],
        chunk_tokens=10,
        chunk_overlap_tokens=3,
    )

    assert chunks == []
