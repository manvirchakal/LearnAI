"""Game idea + code generation, with the validation the old
``server/main.py`` wrote (``validate_js_syntax``, ``post_process_game_code``)
but never actually called from anywhere. One repair round-trip against
the specific violations found, then a clean failure — never a raw model
output or stack trace reaching the client.
"""

from __future__ import annotations

from bson import ObjectId

from learnai.config import LLMTask
from learnai.errors import UpstreamError
from learnai.repositories.artifacts import ArtifactRepository
from learnai.schemas.generation import GameCode, GameIdea
from learnai.services.generation.fingerprint import fingerprint
from learnai.services.generation.game_validator import find_violations
from learnai.services.llm.client import LLMClient
from learnai.services.llm.prompts import render


async def generate_game(
    *,
    llm: LLMClient,
    artifacts: ArtifactRepository,
    collection_id: ObjectId,
    content: str,
    learning_profile_description: str,
) -> tuple[GameIdea, GameCode]:
    fp = fingerprint(kind="game", content=content, learning_profile=learning_profile_description)
    cached = await artifacts.get(collection_id, "game", fp)
    if cached is not None:
        return (
            GameIdea.model_validate(cached["content"]["idea"]),
            GameCode.model_validate(cached["content"]["code"]),
        )

    idea = await llm.structured(
        task=LLMTask.game_idea,
        prompt=render(
            "game_idea.j2", content=content, learning_profile=learning_profile_description
        ),
        schema=GameIdea,
    )
    code = await _generate_validated_code(llm, idea)

    await artifacts.upsert(
        collection_id,
        "game",
        fp,
        {"idea": idea.model_dump(mode="json"), "code": code.model_dump(mode="json")},
    )
    return idea, code


async def _generate_validated_code(llm: LLMClient, idea: GameIdea) -> GameCode:
    prompt = render("game_code.j2", game_idea=idea)
    code = await llm.structured(task=LLMTask.game_code, prompt=prompt, schema=GameCode)
    violations = find_violations(code.javascript)
    if not violations:
        return code

    repair_prompt = (
        f"{prompt}\n\n"
        "Your previous attempt was rejected by an automated safety check "
        "for: " + "; ".join(f"{v.rule} ({v.detail})" for v in violations) + ". "
        "Fix these specific issues — avoid every denied API entirely, "
        "don't work around the check — and try again."
    )
    code = await llm.structured(task=LLMTask.game_code, prompt=repair_prompt, schema=GameCode)
    if find_violations(code.javascript):
        raise UpstreamError("couldn't generate a playable game that passed validation")
    return code
