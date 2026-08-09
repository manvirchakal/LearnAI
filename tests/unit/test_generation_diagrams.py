from __future__ import annotations

from bson import ObjectId

from learnai.config import LLMTask
from learnai.repositories.artifacts import ArtifactRepository
from learnai.schemas.generation import Diagram, DiagramSet
from learnai.services.generation.diagrams import generate_diagrams
from learnai.services.generation.fingerprint import fingerprint
from tests.fakes.llm import FakeLLMClient
from tests.fakes.mongo import FakeAsyncDatabase

_DIAGRAMS = DiagramSet(
    diagrams=[Diagram(title="Overview", mermaid="graph TD\nA[Start] --> B[End]")]
)


async def test_cache_miss_generates_and_caches() -> None:
    db = FakeAsyncDatabase()
    owner = ObjectId()
    artifacts = ArtifactRepository(db, owner)  # type: ignore[arg-type]
    llm = FakeLLMClient(structured_responses={LLMTask.diagrams: _DIAGRAMS})
    collection_id = ObjectId()

    result = await generate_diagrams(
        llm=llm,
        artifacts=artifacts,
        collection_id=collection_id,
        content="material",
        learning_profile_description="visual learner",
    )

    assert result == _DIAGRAMS
    assert llm.calls[0]["task"] == LLMTask.diagrams

    fp = fingerprint(
        kind="diagrams", content="material", learning_profile="visual learner", narrative=""
    )
    assert await artifacts.get(collection_id, "diagrams", fp) is not None


async def test_cache_hit_skips_generation() -> None:
    db = FakeAsyncDatabase()
    owner = ObjectId()
    artifacts = ArtifactRepository(db, owner)  # type: ignore[arg-type]
    collection_id = ObjectId()

    await generate_diagrams(
        llm=FakeLLMClient(structured_responses={LLMTask.diagrams: _DIAGRAMS}),
        artifacts=artifacts,
        collection_id=collection_id,
        content="material",
        learning_profile_description="visual learner",
    )

    broken_llm = FakeLLMClient()
    result = await generate_diagrams(
        llm=broken_llm,
        artifacts=artifacts,
        collection_id=collection_id,
        content="material",
        learning_profile_description="visual learner",
    )

    assert result == _DIAGRAMS
    assert broken_llm.calls == []


async def test_different_narrative_context_is_a_different_cache_key() -> None:
    db = FakeAsyncDatabase()
    owner = ObjectId()
    artifacts = ArtifactRepository(db, owner)  # type: ignore[arg-type]
    collection_id = ObjectId()

    await generate_diagrams(
        llm=FakeLLMClient(structured_responses={LLMTask.diagrams: _DIAGRAMS}),
        artifacts=artifacts,
        collection_id=collection_id,
        content="material",
        learning_profile_description="visual learner",
        narrative=None,
    )

    # Different narrative text -> different fingerprint -> real cache miss,
    # so this must call the LLM again rather than reusing the first result.
    llm = FakeLLMClient(structured_responses={LLMTask.diagrams: _DIAGRAMS})
    await generate_diagrams(
        llm=llm,
        artifacts=artifacts,
        collection_id=collection_id,
        content="material",
        learning_profile_description="visual learner",
        narrative="A summary that changes the fingerprint.",
    )

    assert llm.calls  # was actually called, not served from the first cache entry
