from __future__ import annotations

from learnai.schemas.documents import (
    Citation,
    SectionContent,
    TOCResult,
    TreeNode,
    find_node,
    find_node_path,
)


def _sample_tree() -> list[TreeNode]:
    return [
        TreeNode(
            node_id="1",
            title="Chapter 1",
            start_page=1,
            end_page=20,
            nodes=[
                TreeNode(node_id="1.1", title="1.1 Limits", start_page=1, end_page=10),
                TreeNode(node_id="1.2", title="1.2 Continuity", start_page=11, end_page=20),
            ],
        ),
        TreeNode(node_id="2", title="Chapter 2", start_page=21, end_page=30),
    ]


def test_find_node_locates_a_nested_node() -> None:
    tree = _sample_tree()
    node = find_node(tree, "1.2")
    assert node is not None
    assert node.title == "1.2 Continuity"
    assert node.start_page == 11


def test_find_node_locates_a_top_level_node() -> None:
    tree = _sample_tree()
    node = find_node(tree, "2")
    assert node is not None
    assert node.title == "Chapter 2"


def test_find_node_returns_none_for_unknown_id() -> None:
    assert find_node(_sample_tree(), "9.9") is None


def test_find_node_path_of_nested_node_includes_ancestors() -> None:
    assert find_node_path(_sample_tree(), "1.2") == ["1", "1.2"]


def test_find_node_path_of_top_level_node_is_itself() -> None:
    assert find_node_path(_sample_tree(), "2") == ["2"]


def test_find_node_path_returns_none_for_unknown_id() -> None:
    assert find_node_path(_sample_tree(), "9.9") is None


def test_toc_result_round_trips_through_json() -> None:
    result = TOCResult(tree=_sample_tree(), confidence="high", notes=None)
    restored = TOCResult.model_validate_json(result.model_dump_json())
    assert restored == result


def test_section_content_carries_citations() -> None:
    section = SectionContent(
        node_id="1.1",
        text="The limit of a function...",
        citations=[Citation(cited_text="The limit of a function", start_page=1, end_page=1)],
    )
    assert section.citations[0].start_page == 1
