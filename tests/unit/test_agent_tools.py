"""``build_tools`` against fakes — the 7 owner-scoped chat tools. Each test
drives a tool's handler directly (the same call shape ``AgentTool.handler``
gets from either LLM adapter) rather than through a real model loop.
"""

from __future__ import annotations

import json

import pymupdf
import pytest
from bson import ObjectId

from learnai.config import LLMTask, Settings
from learnai.repositories.artifacts import ArtifactRepository
from learnai.repositories.learning_profiles import LearningProfileRepository
from learnai.repositories.materials import MaterialRepository
from learnai.repositories.sections import SectionRepository
from learnai.schemas.documents import SectionContent, TOCResult, TreeNode
from learnai.schemas.generation import Diagram, DiagramSet
from learnai.services.agent.tools import build_tools
from learnai.services.llm.client import AgentTool
from learnai.services.retrieval.vector_store import Chunk
from tests.fakes.embedder import FakeEmbedder
from tests.fakes.extraction import FakeExtractor
from tests.fakes.llm import FakeLLMClient
from tests.fakes.mongo import FakeAsyncDatabase
from tests.fakes.storage import FakeStorage
from tests.fakes.vector_store import FakeVectorStore


@pytest.fixture
def db() -> FakeAsyncDatabase:
    return FakeAsyncDatabase()


@pytest.fixture
def settings() -> Settings:
    return Settings()


def _make_pdf(num_pages: int) -> bytes:
    doc = pymupdf.open()  # type: ignore[no-untyped-call]
    for _ in range(num_pages):
        doc.new_page()
    buffer: bytes = doc.tobytes()  # type: ignore[no-untyped-call]
    doc.close()  # type: ignore[no-untyped-call]
    return buffer


async def _seed_ready_material(db: FakeAsyncDatabase, owner: ObjectId) -> ObjectId:
    materials = MaterialRepository(db, owner)  # type: ignore[arg-type]
    material_id = await materials.create(
        filename="calculus.pdf", content_type="application/pdf", storage_key="k", size_bytes=1
    )
    tree = TOCResult(
        tree=[TreeNode(node_id="1", title="Limits", start_page=1, end_page=5)], confidence="high"
    )
    await materials.set_toc_result(material_id, tree)
    return material_id


def _tools(
    db: FakeAsyncDatabase,
    owner: ObjectId,
    collection: dict[str, object],
    settings: Settings,
    *,
    vector_store: FakeVectorStore | None = None,
    llm: FakeLLMClient | None = None,
) -> tuple[list[AgentTool], dict[str, object]]:
    deps = {
        "owner_id": owner,
        "collection": collection,
        "materials": MaterialRepository(db, owner),  # type: ignore[arg-type]
        "sections": SectionRepository(db, owner),  # type: ignore[arg-type]
        "storage": FakeStorage(),
        "extractor": FakeExtractor(),
        "embedder": FakeEmbedder(),
        "vector_store": vector_store or FakeVectorStore(),
        "settings": settings,
        "learning_profiles": LearningProfileRepository(db, owner),  # type: ignore[arg-type]
        "artifacts": ArtifactRepository(db, owner),  # type: ignore[arg-type]
        "llm": llm or FakeLLMClient(),
    }
    tools = build_tools(**deps)  # type: ignore[arg-type]
    return tools, deps


def _tool(tools: list[AgentTool], name: str) -> AgentTool:
    return next(t for t in tools if t.name == name)


async def test_list_collection_materials_returns_filenames_and_status(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    material_id = await _seed_ready_material(db, owner)
    collection = {"_id": ObjectId(), "material_refs": [{"material_id": material_id}]}
    tools, _ = _tools(db, owner, collection, settings)

    result = json.loads(await _tool(tools, "list_collection_materials").handler())

    assert result == [
        {"material_id": str(material_id), "filename": "calculus.pdf", "status": "toc_ready"}
    ]


async def test_get_document_tree_returns_tree_json(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    material_id = await _seed_ready_material(db, owner)
    collection = {"_id": ObjectId(), "material_refs": [{"material_id": material_id}]}
    tools, _ = _tools(db, owner, collection, settings)

    result = json.loads(
        await _tool(tools, "get_document_tree").handler(material_id=str(material_id))
    )

    assert result["tree"][0]["title"] == "Limits"


async def test_get_document_tree_not_ready_returns_error_payload(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    materials = MaterialRepository(db, owner)  # type: ignore[arg-type]
    material_id = await materials.create(
        filename="a.pdf", content_type="application/pdf", storage_key="k", size_bytes=1
    )
    collection = {"_id": ObjectId(), "material_refs": [{"material_id": material_id}]}
    tools, _ = _tools(db, owner, collection, settings)

    result = json.loads(
        await _tool(tools, "get_document_tree").handler(material_id=str(material_id))
    )

    assert "error" in result


async def test_get_section_text_lazily_extracts(db: FakeAsyncDatabase, settings: Settings) -> None:
    owner = ObjectId()
    material_id = await _seed_ready_material(db, owner)
    collection = {"_id": ObjectId(), "material_refs": [{"material_id": material_id}]}
    tools, deps = _tools(db, owner, collection, settings)
    storage: FakeStorage = deps["storage"]  # type: ignore[assignment]
    await storage.put("k", _make_pdf(5), "application/pdf")
    extractor: FakeExtractor = deps["extractor"]  # type: ignore[assignment]
    extractor.section_results["1"] = SectionContent(node_id="1", text="the limit of a function...")

    result = await _tool(tools, "get_section_text").handler(
        material_id=str(material_id), node_id="1"
    )

    assert result == "the limit of a function..."


async def test_get_learning_profile_returns_default_when_unset(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    collection = {"_id": ObjectId(), "material_refs": []}
    tools, _ = _tools(db, owner, collection, settings)

    result = await _tool(tools, "get_learning_profile").handler()

    assert result == "No stated learning-style preference yet."


async def test_get_learning_profile_returns_stored_description(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    profiles = LearningProfileRepository(db, owner)  # type: ignore[arg-type]
    await profiles.upsert(
        answers={}, scores={}, description="Visual learner.", questionnaire_version=1
    )
    collection = {"_id": ObjectId(), "material_refs": []}
    tools, _ = _tools(db, owner, collection, settings)

    result = await _tool(tools, "get_learning_profile").handler()

    assert result == "Visual learner."


async def test_get_narrative_returns_error_payload_when_none_generated(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    collection = {"_id": ObjectId(), "material_refs": []}
    tools, _ = _tools(db, owner, collection, settings)

    result = json.loads(await _tool(tools, "get_narrative").handler())

    assert "error" in result


async def test_get_narrative_returns_cached_text(db: FakeAsyncDatabase, settings: Settings) -> None:
    owner = ObjectId()
    collection_id = ObjectId()
    collection = {"_id": collection_id, "material_refs": []}
    artifacts = ArtifactRepository(db, owner)  # type: ignore[arg-type]
    await artifacts.upsert(collection_id, "narrative", "fp1", {"text": "Once upon a time..."})
    tools, _ = _tools(db, owner, collection, settings)

    result = await _tool(tools, "get_narrative").handler()

    assert result == "Once upon a time..."


async def test_generate_diagram_returns_diagram_set_json(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    collection = {"_id": ObjectId(), "material_refs": []}
    diagram_set = DiagramSet(diagrams=[Diagram(title="Overview", mermaid="graph TD\nA-->B")])
    llm = FakeLLMClient(structured_responses={LLMTask.diagrams: diagram_set})
    tools, _ = _tools(db, owner, collection, settings, llm=llm)

    result = json.loads(await _tool(tools, "generate_diagram").handler(topic="limits"))

    assert result["diagrams"][0]["title"] == "Overview"


async def test_search_materials_returns_hits_scoped_to_collection_materials(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    material_id = await _seed_ready_material(db, owner)
    other_material_id = ObjectId()
    collection = {"_id": ObjectId(), "material_refs": [{"material_id": material_id}]}

    vector_store = FakeVectorStore()
    embedder = FakeEmbedder()
    [in_scope_vector] = await embedder.embed(["the limit of a function as x approaches a point"])
    [out_of_scope_vector] = await embedder.embed(["an unrelated chapter from another material"])
    await vector_store.upsert(
        owner_id=owner,
        chunks=[
            Chunk(
                material_id=material_id,
                node_id="1",
                node_path=["1"],
                chunk_index=0,
                page=1,
                title="Limits",
                text="the limit of a function as x approaches a point",
            )
        ],
        vectors=[in_scope_vector],
    )
    await vector_store.upsert(
        owner_id=owner,
        chunks=[
            Chunk(
                material_id=other_material_id,
                node_id="9",
                node_path=["9"],
                chunk_index=0,
                page=1,
                title="Unrelated",
                text="an unrelated chapter from another material",
            )
        ],
        vectors=[out_of_scope_vector],
    )
    tools, _ = _tools(db, owner, collection, settings, vector_store=vector_store)

    result = json.loads(await _tool(tools, "search_materials").handler(query="limit of a function"))

    assert len(result) == 1
    assert result[0]["material_id"] == str(material_id)
    assert result[0]["title"] == "Limits"
