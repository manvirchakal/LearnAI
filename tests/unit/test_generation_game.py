from __future__ import annotations

import pytest
from bson import ObjectId

from learnai.config import LLMTask
from learnai.errors import UpstreamError
from learnai.repositories.artifacts import ArtifactRepository
from learnai.schemas.generation import GameCode, GameIdea
from learnai.services.generation.fingerprint import fingerprint
from learnai.services.generation.game import generate_game
from tests.fakes.llm import FakeLLMClient
from tests.fakes.mongo import FakeAsyncDatabase

_IDEA = GameIdea(
    title="Derivative Dash",
    description="Match a function to its derivative.",
    controls="click",
    mechanics="Click the correct derivative from four options.",
)
_CLEAN_CODE = GameCode(
    instructions="Click the right answer.",
    javascript="return React.createElement('div', null, 'ok');",
)
_UNSAFE_CODE = GameCode(
    instructions="Click the right answer.",
    javascript="document.cookie; return React.createElement('div', null, 'ok');",
)


def _llm(**overrides: object) -> FakeLLMClient:
    return FakeLLMClient(
        structured_responses={LLMTask.game_idea: _IDEA, LLMTask.game_code: _CLEAN_CODE},
        **overrides,  # type: ignore[arg-type]
    )


async def test_cache_miss_generates_idea_and_code_and_caches() -> None:
    db = FakeAsyncDatabase()
    owner = ObjectId()
    artifacts = ArtifactRepository(db, owner)  # type: ignore[arg-type]
    llm = _llm()
    collection_id = ObjectId()

    idea, code = await generate_game(
        llm=llm,
        artifacts=artifacts,
        collection_id=collection_id,
        content="material",
        learning_profile_description="visual learner",
    )

    assert idea == _IDEA
    assert code == _CLEAN_CODE
    assert [c["task"] for c in llm.calls] == [LLMTask.game_idea, LLMTask.game_code]

    fp = fingerprint(kind="game", content="material", learning_profile="visual learner")
    cached = await artifacts.get(collection_id, "game", fp)
    assert cached is not None


async def test_cache_hit_skips_generation() -> None:
    db = FakeAsyncDatabase()
    owner = ObjectId()
    artifacts = ArtifactRepository(db, owner)  # type: ignore[arg-type]
    collection_id = ObjectId()

    await generate_game(
        llm=_llm(),
        artifacts=artifacts,
        collection_id=collection_id,
        content="material",
        learning_profile_description="visual learner",
    )

    broken_llm = FakeLLMClient()  # nothing configured — would KeyError if called
    idea, code = await generate_game(
        llm=broken_llm,
        artifacts=artifacts,
        collection_id=collection_id,
        content="material",
        learning_profile_description="visual learner",
    )

    assert idea == _IDEA
    assert code == _CLEAN_CODE
    assert broken_llm.calls == []


async def test_unsafe_code_triggers_one_repair_round_trip() -> None:
    db = FakeAsyncDatabase()
    owner = ObjectId()
    artifacts = ArtifactRepository(db, owner)  # type: ignore[arg-type]
    llm = _llm(
        structured_response_queue={LLMTask.game_code: [_UNSAFE_CODE, _CLEAN_CODE]},
    )

    _idea, code = await generate_game(
        llm=llm,
        artifacts=artifacts,
        collection_id=ObjectId(),
        content="material",
        learning_profile_description="visual learner",
    )

    assert code == _CLEAN_CODE
    game_code_calls = [c for c in llm.calls if c["task"] == LLMTask.game_code]
    assert len(game_code_calls) == 2
    assert "denied_identifier" in game_code_calls[1]["prompt"]


async def test_repeated_violations_raise_upstream_error_after_one_repair() -> None:
    db = FakeAsyncDatabase()
    owner = ObjectId()
    artifacts = ArtifactRepository(db, owner)  # type: ignore[arg-type]
    llm = _llm(
        structured_response_queue={LLMTask.game_code: [_UNSAFE_CODE, _UNSAFE_CODE]},
    )

    with pytest.raises(UpstreamError, match="couldn't generate a playable game"):
        await generate_game(
            llm=llm,
            artifacts=artifacts,
            collection_id=ObjectId(),
            content="material",
            learning_profile_description="visual learner",
        )

    game_code_calls = [c for c in llm.calls if c["task"] == LLMTask.game_code]
    assert len(game_code_calls) == 2  # exactly one repair attempt, then give up
