"""Generation API — narrative (streamed over SSE), game idea/code, and
diagrams, all scoped to a collection. Shares the same
``/api/v1/collections`` prefix as ``routers/collections.py`` (a separate
router file per the target module layout, same path space).

Content-gathering (``collection_content``) and its errors — a malformed
id, a missing collection, a collection with no ready material — all
happen *before* a streaming response starts, so they come back as normal
``problem+json`` responses through the usual exception handlers. Only a
failure *during* the narrative stream itself (after a 200 has already
gone out) gets the SSE ``event: error`` treatment — the status code
can't change at that point.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from learnai.deps import (
    ArtifactRepoDep,
    CollectionRepoDep,
    CurrentUser,
    EmbedderDep,
    ExtractorDep,
    LearningProfileRepoDep,
    LLMClientDep,
    MaterialRepoDep,
    SectionRepoDep,
    SettingsDep,
    StorageDep,
    VectorStoreDep,
)
from learnai.errors import AppError, ValidationError
from learnai.repositories.learning_profiles import LearningProfileRepository
from learnai.schemas.generation import DiagramSet, GameCode, GameIdea
from learnai.services.generation.context import collection_content
from learnai.services.generation.diagrams import generate_diagrams
from learnai.services.generation.game import generate_game
from learnai.services.generation.narrative import stream_narrative

router = APIRouter(prefix="/api/v1/collections", tags=["generation"])

_NO_PROFILE_DESCRIPTION = "No stated learning-style preference yet."


def _object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId as exc:
        raise ValidationError(f"invalid id: {value!r}") from exc


async def _learning_profile_description(repo: LearningProfileRepository) -> str:
    profile = await repo.get()
    return profile["description"] if profile is not None else _NO_PROFILE_DESCRIPTION


class GameOut(BaseModel):
    idea: GameIdea
    code: GameCode


class DiagramsRequest(BaseModel):
    # The frontend already has the streamed narrative text by the time it
    # asks for diagrams — passing it back gives the model extra context it
    # otherwise has no way to see, without the router reaching into the
    # narrative artifact's cache internals to guess whether one exists.
    narrative: str | None = None


@router.get("/{collection_id}/narrative")
async def get_narrative(
    collection_id: str,
    collections: CollectionRepoDep,
    learning_profiles: LearningProfileRepoDep,
    materials: MaterialRepoDep,
    sections: SectionRepoDep,
    storage: StorageDep,
    extractor: ExtractorDep,
    embedder: EmbedderDep,
    vector_store: VectorStoreDep,
    settings: SettingsDep,
    artifacts: ArtifactRepoDep,
    llm: LLMClientDep,
    user: CurrentUser,
) -> StreamingResponse:
    coll_id = _object_id(collection_id)
    collection = await collections.get(coll_id)
    content = await collection_content(
        collection,
        materials=materials,
        sections=sections,
        storage=storage,
        extractor=extractor,
        embedder=embedder,
        vector_store=vector_store,
        settings=settings,
        owner_id=user["_id"],
    )
    profile_description = await _learning_profile_description(learning_profiles)

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for chunk in stream_narrative(
                llm=llm,
                artifacts=artifacts,
                collection_id=coll_id,
                content=content,
                learning_profile_description=profile_description,
            ):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            yield "event: done\ndata: {}\n\n"
        except AppError as exc:
            yield f"event: error\ndata: {json.dumps({'detail': exc.message})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{collection_id}/game", response_model=GameOut)
async def post_game(
    collection_id: str,
    collections: CollectionRepoDep,
    learning_profiles: LearningProfileRepoDep,
    materials: MaterialRepoDep,
    sections: SectionRepoDep,
    storage: StorageDep,
    extractor: ExtractorDep,
    embedder: EmbedderDep,
    vector_store: VectorStoreDep,
    settings: SettingsDep,
    artifacts: ArtifactRepoDep,
    llm: LLMClientDep,
    user: CurrentUser,
) -> GameOut:
    coll_id = _object_id(collection_id)
    collection = await collections.get(coll_id)
    content = await collection_content(
        collection,
        materials=materials,
        sections=sections,
        storage=storage,
        extractor=extractor,
        embedder=embedder,
        vector_store=vector_store,
        settings=settings,
        owner_id=user["_id"],
    )
    profile_description = await _learning_profile_description(learning_profiles)

    idea, code = await generate_game(
        llm=llm,
        artifacts=artifacts,
        collection_id=coll_id,
        content=content,
        learning_profile_description=profile_description,
    )
    return GameOut(idea=idea, code=code)


@router.post("/{collection_id}/diagrams", response_model=DiagramSet)
async def post_diagrams(
    collection_id: str,
    collections: CollectionRepoDep,
    learning_profiles: LearningProfileRepoDep,
    materials: MaterialRepoDep,
    sections: SectionRepoDep,
    storage: StorageDep,
    extractor: ExtractorDep,
    embedder: EmbedderDep,
    vector_store: VectorStoreDep,
    settings: SettingsDep,
    artifacts: ArtifactRepoDep,
    llm: LLMClientDep,
    user: CurrentUser,
    body: DiagramsRequest = DiagramsRequest(),
) -> DiagramSet:
    coll_id = _object_id(collection_id)
    collection = await collections.get(coll_id)
    content = await collection_content(
        collection,
        materials=materials,
        sections=sections,
        storage=storage,
        extractor=extractor,
        embedder=embedder,
        vector_store=vector_store,
        settings=settings,
        owner_id=user["_id"],
    )
    profile_description = await _learning_profile_description(learning_profiles)

    return await generate_diagrams(
        llm=llm,
        artifacts=artifacts,
        collection_id=coll_id,
        content=content,
        learning_profile_description=profile_description,
        narrative=body.narrative,
    )
