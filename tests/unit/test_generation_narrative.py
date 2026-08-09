from __future__ import annotations

from bson import ObjectId

from learnai.config import LLMTask
from learnai.repositories.artifacts import ArtifactRepository
from learnai.services.generation.fingerprint import fingerprint
from learnai.services.generation.narrative import stream_narrative
from tests.fakes.llm import FakeLLMClient
from tests.fakes.mongo import FakeAsyncDatabase


async def test_streams_chunks_and_caches_full_text() -> None:
    db = FakeAsyncDatabase()
    owner = ObjectId()
    artifacts = ArtifactRepository(db, owner)  # type: ignore[arg-type]
    llm = FakeLLMClient(stream_chunks={LLMTask.narrative: ["Once ", "upon ", "a time."]})
    collection_id = ObjectId()

    chunks = [
        chunk
        async for chunk in stream_narrative(
            llm=llm,
            artifacts=artifacts,
            collection_id=collection_id,
            content="material",
            learning_profile_description="visual learner",
        )
    ]

    assert chunks == ["Once ", "upon ", "a time."]
    assert llm.calls[0]["task"] == LLMTask.narrative

    fp = fingerprint(kind="narrative", content="material", learning_profile="visual learner")
    cached = await artifacts.get(collection_id, "narrative", fp)
    assert cached is not None
    assert cached["content"]["text"] == "Once upon a time."


async def test_cache_hit_yields_cached_text_without_calling_the_llm() -> None:
    db = FakeAsyncDatabase()
    owner = ObjectId()
    artifacts = ArtifactRepository(db, owner)  # type: ignore[arg-type]
    collection_id = ObjectId()

    seeding_llm = FakeLLMClient(stream_chunks={LLMTask.narrative: ["cached text"]})
    async for _ in stream_narrative(
        llm=seeding_llm,
        artifacts=artifacts,
        collection_id=collection_id,
        content="material",
        learning_profile_description="visual learner",
    ):
        pass

    broken_llm = FakeLLMClient()  # no stream_chunks configured — would KeyError if called
    chunks = [
        chunk
        async for chunk in stream_narrative(
            llm=broken_llm,
            artifacts=artifacts,
            collection_id=collection_id,
            content="material",
            learning_profile_description="visual learner",
        )
    ]

    assert chunks == ["cached text"]
    assert broken_llm.calls == []
