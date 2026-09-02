from __future__ import annotations

from learnai.services.asr import TranscriptResult, TranscriptSegment
from learnai.services.ingestion.media import group_transcript_into_tree


def test_empty_transcript_produces_empty_tree() -> None:
    transcript = TranscriptResult(language="en", segments=[])

    tree, sections = group_transcript_into_tree(transcript, title="Lecture 1")

    assert tree.tree == []
    assert tree.confidence == "low"
    assert sections == []


def test_short_transcript_is_a_single_bucket() -> None:
    transcript = TranscriptResult(
        language="en",
        segments=[
            TranscriptSegment(start=0.0, end=2.0, text="Hello everyone."),
            TranscriptSegment(start=2.0, end=5.0, text="Today we cover limits."),
        ],
    )

    tree, sections = group_transcript_into_tree(transcript, title="Calculus Lecture 1")

    assert len(tree.tree) == 1
    assert tree.tree[0].node_id == "1"
    assert tree.tree[0].title == "Calculus Lecture 1 (0:00-0:05)"
    assert tree.tree[0].start_page == 1
    assert tree.tree[0].end_page == 1
    assert len(sections) == 1
    assert sections[0].node_id == "1"
    assert sections[0].text == "Hello everyone. Today we cover limits."


def test_long_transcript_is_split_into_time_buckets() -> None:
    # 5-minute buckets — a segment starting at 6 minutes must land in a new
    # bucket from one starting at 0.
    transcript = TranscriptResult(
        language="en",
        segments=[
            TranscriptSegment(start=0.0, end=10.0, text="Part one."),
            TranscriptSegment(start=360.0, end=370.0, text="Part two."),
        ],
    )

    tree, sections = group_transcript_into_tree(transcript, title="Lecture")

    assert len(tree.tree) == 2
    assert [node.node_id for node in tree.tree] == ["1", "2"]
    assert sections[0].text == "Part one."
    assert sections[1].text == "Part two."
    # Minute-marker placeholders, not real page numbers.
    assert tree.tree[0].start_page == 1
    assert tree.tree[1].start_page == 7  # int(360 // 60) + 1


def test_node_ids_line_up_with_section_ids() -> None:
    transcript = TranscriptResult(
        language="en",
        segments=[
            TranscriptSegment(start=0.0, end=10.0, text="a"),
            TranscriptSegment(start=400.0, end=410.0, text="b"),
            TranscriptSegment(start=900.0, end=910.0, text="c"),
        ],
    )

    tree, sections = group_transcript_into_tree(transcript, title="Lecture")

    assert [node.node_id for node in tree.tree] == [s.node_id for s in sections]
