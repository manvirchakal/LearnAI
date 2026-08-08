"""Tree-aware chunking — bounded windows over a single section's text,
never spanning two nodes: every chunk carries exactly one ``node_id`` (see
the modernization plan's "Retrieval: tree-scoped vector search"). Default
size/overlap come from ``settings.chunk_tokens``/``chunk_overlap_tokens``
(512/64) — "tokens" here means whitespace-split words, not a real subword
tokenizer. That's an approximation, but a good-enough one to bound chunk
size for embedding and keep results readable, without pulling in a
tokenizer dependency for this alone.

Every chunk from a section is stamped with that node's own ``start_page``
— the section's transcribed text is a flat string with no per-page
markers, so a chunk's exact page within a multi-page section isn't
recoverable here; precise page provenance for a specific passage still
comes from ``SectionContent.citations``, used directly by the reader.
"""

from __future__ import annotations

from bson import ObjectId

from learnai.schemas.documents import SectionContent, TreeNode
from learnai.services.retrieval.vector_store import Chunk


def chunk_text(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    step = max(chunk_size - overlap, 1)
    chunks: list[str] = []
    start = 0
    while start < len(words):
        chunks.append(" ".join(words[start : start + chunk_size]))
        if start + chunk_size >= len(words):
            break
        start += step
    return chunks


def chunk_section(
    section: SectionContent,
    *,
    material_id: ObjectId,
    node: TreeNode,
    node_path: list[str],
    chunk_tokens: int,
    chunk_overlap_tokens: int,
) -> list[Chunk]:
    texts = chunk_text(section.text, chunk_size=chunk_tokens, overlap=chunk_overlap_tokens)
    return [
        Chunk(
            material_id=material_id,
            node_id=section.node_id,
            node_path=node_path,
            chunk_index=index,
            page=node.start_page,
            title=node.title,
            text=text,
        )
        for index, text in enumerate(texts)
    ]
