"""Renders the Phase 5 prompt templates against representative context.
Not full golden-file snapshots (nothing established that pattern in this
codebase yet — see ``services/llm/prompts.py``'s docstring aspiration);
this instead asserts every template renders cleanly and the values passed
in actually appear in the output, which is what would catch a broken
Jinja reference or a dropped variable.
"""

from __future__ import annotations

from learnai.schemas.generation import GameControls, GameIdea
from learnai.services.llm.prompts import render


def test_narrative_includes_content_and_profile() -> None:
    prompt = render(
        "narrative.j2", content="Newton's laws of motion.", learning_profile="visual learner"
    )
    assert "Newton's laws of motion." in prompt
    assert "visual learner" in prompt


def test_game_idea_includes_content_and_profile() -> None:
    prompt = render(
        "game_idea.j2", content="The chain rule.", learning_profile="kinesthetic learner"
    )
    assert "The chain rule." in prompt
    assert "kinesthetic learner" in prompt


def test_game_code_includes_game_idea_fields() -> None:
    idea = GameIdea(
        title="Derivative Dash",
        description="Match a function to its derivative before time runs out.",
        controls="click",
        mechanics="Click the correct derivative from four options.",
    )
    prompt = render("game_code.j2", game_idea=idea)

    assert "Derivative Dash" in prompt
    assert "Match a function to its derivative before time runs out." in prompt
    assert "Click the correct derivative from four options." in prompt
    assert "onClick" in prompt  # the click-specific branch, not another control's


_CONTROL_CASES: list[tuple[GameControls, str]] = [
    ("arrow_keys", "keydown"),
    ("click", "onClick"),
    ("type_answer", "controlled text input"),
    ("drag_and_drop", "onDrop"),
]


def test_game_code_branches_by_controls() -> None:
    for controls, expected_snippet in _CONTROL_CASES:
        idea = GameIdea(title="t", description="d", controls=controls, mechanics="m")
        prompt = render("game_code.j2", game_idea=idea)
        assert expected_snippet in prompt, f"missing {expected_snippet!r} for controls={controls}"


def test_diagrams_includes_content_and_optional_narrative() -> None:
    without_narrative = render(
        "diagrams.j2", content="Cell division.", learning_profile="visual learner", narrative=None
    )
    assert "Cell division." in without_narrative
    assert "Summary already written" not in without_narrative

    with_narrative = render(
        "diagrams.j2",
        content="Cell division.",
        learning_profile="visual learner",
        narrative="Mitosis has four phases.",
    )
    assert "Mitosis has four phases." in with_narrative
    assert "Summary already written" in with_narrative


def test_chat_system_includes_profile() -> None:
    prompt = render("chat_system.j2", learning_profile="auditory learner")
    assert "auditory learner" in prompt
    assert "search_materials" in prompt


def test_translation_includes_text_and_target_language() -> None:
    prompt = render("translation.j2", text="The limit of a function.", target_language="es-ES")
    assert "The limit of a function." in prompt
    assert "es-ES" in prompt
