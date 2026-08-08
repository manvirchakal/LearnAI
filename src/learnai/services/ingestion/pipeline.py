"""Lazy per-section extraction: the second half of the ingestion pipeline
after the worker's TOC pass (``worker/tasks.extract_toc_task``). Unlike the
TOC pass — a handful of pages, run once as a background job — a section is
extracted the first time someone opens it, synchronously, and cached
forever after (see ``SectionRepository``). That's the cost mitigation the
modernization plan calls out: most sections of most uploads never get
read, so there is no eager whole-book extraction to pay for.
"""

from __future__ import annotations

from bson import ObjectId

from learnai.errors import Conflict, NotFound
from learnai.repositories.materials import MaterialRepository
from learnai.repositories.sections import SectionRepository
from learnai.schemas.documents import SectionContent, TOCResult, find_node
from learnai.services.extraction.base import DocumentExtractor
from learnai.services.ingestion.pdf import slice_pages
from learnai.services.storage.base import StorageBackend


async def get_or_extract_section(
    *,
    materials: MaterialRepository,
    sections: SectionRepository,
    storage: StorageBackend,
    extractor: DocumentExtractor,
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
    return section
