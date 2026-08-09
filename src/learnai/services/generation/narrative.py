"""Narrative generation — streamed to the client over SSE, cached whole
once complete. A cache hit replays the full cached text as a single
chunk rather than a fresh word-by-word stream; the point of caching is
skipping the LLM call, not simulating latency that no longer exists.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from bson import ObjectId

from learnai.config import LLMTask
from learnai.repositories.artifacts import ArtifactRepository
from learnai.services.generation.fingerprint import fingerprint
from learnai.services.llm.client import LLMClient
from learnai.services.llm.prompts import render


async def stream_narrative(
    *,
    llm: LLMClient,
    artifacts: ArtifactRepository,
    collection_id: ObjectId,
    content: str,
    learning_profile_description: str,
) -> AsyncIterator[str]:
    fp = fingerprint(
        kind="narrative", content=content, learning_profile=learning_profile_description
    )
    cached = await artifacts.get(collection_id, "narrative", fp)
    if cached is not None:
        yield cached["content"]["text"]
        return

    prompt = render("narrative.j2", content=content, learning_profile=learning_profile_description)
    chunks: list[str] = []
    async for chunk in llm.stream(task=LLMTask.narrative, prompt=prompt):
        chunks.append(chunk)
        yield chunk

    await artifacts.upsert(collection_id, "narrative", fp, {"text": "".join(chunks)})
