"""The game agent's tools: line-numbered views, whole writes and exact, unique edits, each saved at once."""
import pytest
from langchain.tools import ToolRuntime

from agents import game_tools
from agents.game_tools import GameArtifact, GameContext, edit_game, view_game, write_game
from services.storage_service import load_game_session

KEY = ("tools-user", "book", "s1")
CODE = "const a = 1;\nconst b = 2;\nconst a2 = 1;\nreturn React.createElement('div', null, a + b);"


@pytest.fixture
def context() -> GameContext:
    return GameContext(*KEY, GameArtifact(CODE, version=4))


def runtime(context) -> ToolRuntime:
    return ToolRuntime(state=None, context=context, config={}, stream_writer=None,
                       tool_call_id="call-0", store=None)


def test_view_numbers_lines_and_pages(context, monkeypatch):
    out = view_game.func(runtime=runtime(context), start_line=2, end_line=3)
    assert out == "Lines 2-3 of 4 (version 4):\n2 | const b = 2;\n3 | const a2 = 1;"
    monkeypatch.setattr(game_tools, "VIEW_MAX_LINES", 2)
    out = view_game.func(runtime=runtime(context))
    assert out.endswith("[Continues: view_game(start_line=3)]") and "3 |" not in out
    assert "outside the game" in view_game.func(runtime=runtime(context), start_line=9)


def test_write_strips_fences_and_saves(context):
    out = write_game.func(code="```javascript\nreturn null;\n```", runtime=runtime(context))
    assert out == "Wrote the game: 1 lines (version 5)."
    assert context.artifact.code == "return null;"
    assert load_game_session(*KEY) == {"code": "return null;", "version": 5}


def test_edit_replaces_one_exact_match(context):
    out = edit_game.func(old_text="const b = 2;", new_text="const b = 3;\nconst c = 4;", runtime=runtime(context))
    assert out.startswith("Edited lines 2-3 (version 5). Now:\n1 | const a = 1;\n2 | const b = 3;\n3 | const c = 4;")
    assert context.artifact.code == CODE.replace("const b = 2;", "const b = 3;\nconst c = 4;")
    assert load_game_session(*KEY)["version"] == 5


def test_edit_refuses_missing_or_ambiguous_text(context):
    assert "not found" in edit_game.func(old_text="const z", new_text="", runtime=runtime(context))
    assert "appears 2 times" in edit_game.func(old_text="= 1;", new_text="= 9;", runtime=runtime(context))
    assert context.artifact == GameArtifact(CODE, version=4)
