"""The document tree — TOC structure and extracted section content.

Node schema deliberately matches `PageIndex <https://github.com/VectifyAI/PageIndex>`_'s
(``node_id``, ``title``, ``start_index``/``end_index``, ``summary``, nested
``nodes``) — a vectorless RAG framework that builds the same shape of tree.
We build it ourselves via Claude's native PDF reading (see
``services/extraction/``) instead of PageIndex's own per-node LLM indexing
pass and 30+-second tree-search reasoning: no per-node indexing cost, no
dependency on their PDF→Markdown path. Matching their node shape keeps a
future swap to real PageIndex tree search cheap if ever wanted for an
async, quality-critical surface. The tree also doubles as the retrieval
index (Phase 4: scope vector search to a subtree) and the reader's
navigation sidebar.

These are domain objects, not just API request/response shapes: the
extraction service returns them, ``MaterialRepository`` stores them (as
plain dicts — Mongo doesn't need the Pydantic wrapper), and routers
serialize them back out.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TreeNode(BaseModel):
    node_id: str  # stable, path-derived: "1", "1.2", "1.2.3"
    title: str
    start_page: int
    end_page: int
    summary: str | None = None
    nodes: list[TreeNode] = Field(default_factory=list)


class TOCResult(BaseModel):
    tree: list[TreeNode]
    confidence: Literal["high", "medium", "low"]
    notes: str | None = None  # e.g. "pages 3-4 unreadable"


class Citation(BaseModel):
    cited_text: str
    start_page: int
    end_page: int


class SectionContent(BaseModel):
    node_id: str
    text: str
    citations: list[Citation] = Field(default_factory=list)


def find_node(nodes: list[TreeNode], node_id: str) -> TreeNode | None:
    """Depth-first search of a tree (or subtree) for a node by id."""
    for node in nodes:
        if node.node_id == node_id:
            return node
        found = find_node(node.nodes, node_id)
        if found is not None:
            return found
    return None
