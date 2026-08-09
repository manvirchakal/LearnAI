"""Diagram generation — structured Mermaid output, replacing the old
``server/main.py``'s regex scrape of ```mermaid fences out of free text.
"""

from __future__ import annotations

from bson import ObjectId

from learnai.config import LLMTask
from learnai.repositories.artifacts import ArtifactRepository
from learnai.schemas.generation import DiagramSet
from learnai.services.generation.fingerprint import fingerprint
from learnai.services.llm.client import LLMClient
from learnai.services.llm.prompts import render


async def generate_diagrams(
    *,
    llm: LLMClient,
    artifacts: ArtifactRepository,
    collection_id: ObjectId,
    content: str,
    learning_profile_description: str,
    narrative: str | None = None,
) -> DiagramSet:
    fp = fingerprint(
        kind="diagrams",
        content=content,
        learning_profile=learning_profile_description,
        narrative=narrative or "",
    )
    cached = await artifacts.get(collection_id, "diagrams", fp)
    if cached is not None:
        return DiagramSet.model_validate(cached["content"])

    result = await llm.structured(
        task=LLMTask.diagrams,
        prompt=render(
            "diagrams.j2",
            content=content,
            learning_profile=learning_profile_description,
            narrative=narrative,
        ),
        schema=DiagramSet,
    )
    await artifacts.upsert(collection_id, "diagrams", fp, result.model_dump(mode="json"))
    return result
