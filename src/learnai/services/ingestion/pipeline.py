"""Lazy per-section extraction: the second half of the ingestion pipeline
after the worker's TOC pass (``worker/tasks.extract_toc_task``). Unlike the
TOC pass — a handful of pages, run once as a background job — a section is
extracted the first time someone opens it, synchronously, and cached
forever after (see ``SectionRepository``). That's the cost mitigation the
modernization plan calls out: most sections of most uploads never get
read, so there is no eager whole-book extraction to pay for.

A fresh extraction (never a cache hit — the chunks are already indexed
from the first time) is also chunked, embedded, and upserted into the
vector store, piggybacking retrieval indexing onto the same cost
mitigation: a section only ever gets indexed if someone actually read it.
"""

from __future__ import annotations

from bson import ObjectId

from learnai.config import Settings
from learnai.errors import Conflict, NotFound
from learnai.logging import get_logger
from learnai.repositories.materials import MaterialRepository
from learnai.repositories.sections import SectionRepository
from learnai.schemas.documents import SectionContent, TOCResult, TreeNode, find_node, find_node_path
from learnai.services.extraction.base import DocumentExtractor
from learnai.services.ingestion.pdf import slice_pages
from learnai.services.retrieval.chunker import chunk_section
from learnai.services.retrieval.embedder import Embedder
from learnai.services.retrieval.vector_store import VectorStore
from learnai.services.storage.base import StorageBackend

logger = get_logger(__name__)


async def get_or_extract_section(
    *,
    materials: MaterialRepository,
    sections: SectionRepository,
    storage: StorageBackend,
    extractor: DocumentExtractor,
    embedder: Embedder,
    vector_store: VectorStore,
    settings: Settings,
    owner_id: ObjectId,
    material_id: ObjectId,
    node_id: str,
) -> SectionContent:
    cached = await sections.get(material_id, node_id)
    if cached is not None:
        return SectionContent.model_validate(cached)

    material = await materials.get(material_id)
    if material["status"] != "toc_ready":
        raise Conflict(f"material {material_id} has no ready document tree yet")

    tree = TOCResult.model_validate(material["tree"])
    node = find_node(tree.tree, node_id)
    if node is None:
        raise NotFound(f"section {node_id} not found in material {material_id}")

    pdf_bytes = await storage.get(material["storage_key"])
    excerpt = slice_pages(pdf_bytes, start_page=node.start_page, end_page=node.end_page)

    ref = await extractor.upload(excerpt, filename=material["filename"])
    try:
        section = await extractor.extract_section(
            ref, node_id=node_id, page_offset=node.start_page - 1
        )
    finally:
        await extractor.delete(ref)

    await sections.upsert(material_id, section)

    try:
        await _index_section(
            section,
            material_id=material_id,
            node=node,
            node_path=find_node_path(tree.tree, node_id) or [node_id],
            embedder=embedder,
            vector_store=vector_store,
            settings=settings,
            owner_id=owner_id,
        )
    except Exception:
        # Indexing is a search-quality enhancement, not part of the read
        # path's correctness — a Qdrant/embedder outage must not stop
        # someone from reading a section they just paid to extract.
        logger.error(
            "section_indexing_failed",
            material_id=str(material_id),
            node_id=node_id,
            exc_info=True,
        )

    return section


async def _index_section(
    section: SectionContent,
    *,
    material_id: ObjectId,
    node: TreeNode,
    node_path: list[str],
    embedder: Embedder,
    vector_store: VectorStore,
    settings: Settings,
    owner_id: ObjectId,
) -> None:
    chunks = chunk_section(
        section,
        material_id=material_id,
        node=node,
        node_path=node_path,
        chunk_tokens=settings.chunk_tokens,
        chunk_overlap_tokens=settings.chunk_overlap_tokens,
    )
    if not chunks:
        return
    vectors = await embedder.embed([chunk.text for chunk in chunks])
    await vector_store.upsert(owner_id=owner_id, chunks=chunks, vectors=vectors)
