"""Gathers a collection's material content for generation — the "Primary
Content from Collection" the old ``server/main.py`` built ad hoc at each
of its three generation call sites. Reuses ``get_or_extract_section``
directly, so gathering content for generation is exactly the same lazy-
extraction-and-index path a reader hitting "read this section" goes
through — no separate eager-extraction code path to keep in sync.
"""

from __future__ import annotations

from typing import Any

from bson import ObjectId

from learnai.config import Settings
from learnai.errors import ValidationError
from learnai.repositories.materials import MaterialRepository
from learnai.repositories.sections import SectionRepository
from learnai.schemas.documents import TOCResult, find_node
from learnai.services.extraction.base import DocumentExtractor
from learnai.services.ingestion.pipeline import get_or_extract_section
from learnai.services.retrieval.embedder import Embedder
from learnai.services.retrieval.vector_store import VectorStore
from learnai.services.storage.base import StorageBackend


async def collection_content(
    collection: dict[str, Any],
    *,
    materials: MaterialRepository,
    sections: SectionRepository,
    storage: StorageBackend,
    extractor: DocumentExtractor,
    embedder: Embedder,
    vector_store: VectorStore,
    settings: Settings,
    owner_id: ObjectId,
) -> str:
    parts: list[str] = []
    for ref in collection.get("material_refs", []):
        material_id = ref["material_id"]
        material = await materials.get(material_id)
        if material["status"] != "toc_ready":
            continue  # not extracted yet — skip rather than fail the whole generation

        tree = TOCResult.model_validate(material["tree"])
        # Empty section_ids means "the whole material" — every top-level
        # node, not a full recursive leaf walk (which could eagerly
        # extract far more than anyone asked to read).
        node_ids: list[str] = ref.get("section_ids") or [node.node_id for node in tree.tree]

        for node_id in node_ids:
            node = find_node(tree.tree, node_id)
            if node is None:
                continue  # a stale reference to a node that no longer exists
            section = await get_or_extract_section(
                materials=materials,
                sections=sections,
                storage=storage,
                extractor=extractor,
                embedder=embedder,
                vector_store=vector_store,
                settings=settings,
                owner_id=owner_id,
                material_id=material_id,
                node_id=node_id,
            )
            parts.append(f"## {material['filename']} — {node.title}\n\n{section.text}")

    if not parts:
        raise ValidationError("collection has no ready material content to generate from")
    return "\n\n".join(parts)
