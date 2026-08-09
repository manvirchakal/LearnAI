"""The chat agent's tools — each closes over the authenticated ``owner_id``
(and the collection the conversation is scoped to), so a tool physically
cannot read another user's data or another collection's materials. Built
fresh per chat request by ``build_tools`` in ``services/agent/chat_agent.py``,
from the same repositories/services the generation and retrieval routers
already use — no new data-access path, just a new caller.

Every handler returns ``str`` (``AgentTool.handler``'s contract) — plain
text for narrative/profile text, JSON for anything structured (search
hits, a document tree, a material list) so the model can read field names
directly and ``chat_agent.py`` can parse the same JSON back out to build
citations from ``search_materials`` calls.
"""

from __future__ import annotations

import json
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, Field

from learnai.config import Settings
from learnai.repositories.artifacts import ArtifactRepository
from learnai.repositories.learning_profiles import LearningProfileRepository
from learnai.repositories.materials import MaterialRepository
from learnai.repositories.sections import SectionRepository
from learnai.services.extraction.base import DocumentExtractor
from learnai.services.generation.diagrams import generate_diagrams
from learnai.services.ingestion.pipeline import get_or_extract_section
from learnai.services.llm.client import AgentTool, LLMClient
from learnai.services.retrieval.embedder import Embedder
from learnai.services.retrieval.retriever import search_materials
from learnai.services.retrieval.vector_store import VectorStore
from learnai.services.storage.base import StorageBackend

_NO_PROFILE_DESCRIPTION = "No stated learning-style preference yet."


class SearchMaterialsArgs(BaseModel):
    query: str = Field(description="What to search for in the collection's materials.")
    scope_node_id: str | None = Field(
        default=None,
        description=(
            "Restrict the search to this chapter/section node id (from "
            "get_document_tree) and its descendants — use this when the "
            "question is about a specific, already-known part of the "
            "material. Omit for a broader, cross-cutting search."
        ),
    )


class GetDocumentTreeArgs(BaseModel):
    material_id: str = Field(description="A material id from list_collection_materials.")


class GetSectionTextArgs(BaseModel):
    material_id: str = Field(description="A material id from list_collection_materials.")
    node_id: str = Field(description="A node id from that material's document tree.")


class NoArgs(BaseModel):
    pass


class GenerateDiagramArgs(BaseModel):
    topic: str = Field(description="What the diagram should illustrate.")


def build_tools(
    *,
    owner_id: ObjectId,
    collection: dict[str, Any],
    materials: MaterialRepository,
    sections: SectionRepository,
    storage: StorageBackend,
    extractor: DocumentExtractor,
    embedder: Embedder,
    vector_store: VectorStore,
    settings: Settings,
    learning_profiles: LearningProfileRepository,
    artifacts: ArtifactRepository,
    llm: LLMClient,
) -> list[AgentTool]:
    collection_id: ObjectId = collection["_id"]
    material_ids: list[ObjectId] = [
        ref["material_id"] for ref in collection.get("material_refs", [])
    ]

    async def _profile_description() -> str:
        profile = await learning_profiles.get()
        return profile["description"] if profile is not None else _NO_PROFILE_DESCRIPTION

    async def _search_materials(query: str, scope_node_id: str | None = None) -> str:
        hits = []
        for material_id in material_ids:
            hits.extend(
                await search_materials(
                    query,
                    owner_id=owner_id,
                    embedder=embedder,
                    vector_store=vector_store,
                    material_id=material_id,
                    scope_node_id=scope_node_id,
                    limit=5,
                )
            )
        hits.sort(key=lambda h: h.score, reverse=True)
        return json.dumps(
            [
                {
                    "material_id": str(hit.material_id),
                    "node_id": hit.node_id,
                    "title": hit.title,
                    "page": hit.page,
                    "text": hit.text,
                    "score": hit.score,
                }
                for hit in hits[:5]
            ]
        )

    async def _get_document_tree(material_id: str) -> str:
        material = await materials.get(ObjectId(material_id))
        if material["tree"] is None:
            return json.dumps({"error": "this material's table of contents isn't ready yet"})
        return json.dumps(material["tree"])

    async def _get_section_text(material_id: str, node_id: str) -> str:
        section = await get_or_extract_section(
            materials=materials,
            sections=sections,
            storage=storage,
            extractor=extractor,
            embedder=embedder,
            vector_store=vector_store,
            settings=settings,
            owner_id=owner_id,
            material_id=ObjectId(material_id),
            node_id=node_id,
        )
        return section.text

    async def _list_collection_materials() -> str:
        items = []
        for material_id in material_ids:
            material = await materials.get(material_id)
            items.append(
                {
                    "material_id": str(material_id),
                    "filename": material["filename"],
                    "status": material["status"],
                }
            )
        return json.dumps(items)

    async def _get_learning_profile() -> str:
        return await _profile_description()

    async def _generate_diagram(topic: str) -> str:
        diagram_set = await generate_diagrams(
            llm=llm,
            artifacts=artifacts,
            collection_id=collection_id,
            content=topic,
            learning_profile_description=await _profile_description(),
        )
        return diagram_set.model_dump_json()

    async def _get_narrative() -> str:
        artifact = await artifacts.get_latest(collection_id, "narrative")
        if artifact is None:
            return json.dumps({"error": "no narrative has been generated for this collection yet"})
        text: str = artifact["content"]["text"]
        return text

    return [
        AgentTool(
            name="search_materials",
            description=(
                "Search this collection's materials for content relevant to a "
                "question. Returns up to 5 passages with their material_id, "
                "node_id, title, page, and text, most relevant first."
            ),
            args_schema=SearchMaterialsArgs,
            handler=_search_materials,
        ),
        AgentTool(
            name="get_document_tree",
            description="Get a material's table-of-contents tree (chapters/sections with node ids).",
            args_schema=GetDocumentTreeArgs,
            handler=_get_document_tree,
        ),
        AgentTool(
            name="get_section_text",
            description="Get the full extracted text of one section of a material.",
            args_schema=GetSectionTextArgs,
            handler=_get_section_text,
        ),
        AgentTool(
            name="list_collection_materials",
            description="List the materials (id, filename, extraction status) in this collection.",
            args_schema=NoArgs,
            handler=_list_collection_materials,
        ),
        AgentTool(
            name="get_learning_profile",
            description="Get the user's stated learning-style preference description.",
            args_schema=NoArgs,
            handler=_get_learning_profile,
        ),
        AgentTool(
            name="generate_diagram",
            description="Generate a Mermaid diagram illustrating a topic from this collection.",
            args_schema=GenerateDiagramArgs,
            handler=_generate_diagram,
        ),
        AgentTool(
            name="get_narrative",
            description="Get the most recently generated study narrative for this collection, if any.",
            args_schema=NoArgs,
            handler=_get_narrative,
        ),
    ]
