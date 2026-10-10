"""
Tools the game agent calls to write and edit the game artifact: the BODY of a
Game() component, stored per unit in the game session (storage_service).

    view_game   the code with line numbers, VIEW_MAX_LINES at a time; errors
                from the browser cite these line numbers
    write_game  replace the whole artifact (the first draft)
    edit_game   replace one exact, unique snippet (fixes)

Every write saves the artifact at once with a new version, so the backend
always holds the code the agent last wrote, and the frontend's error reports
say which version they came from.
"""
from dataclasses import dataclass, field

from langchain.tools import ToolRuntime, tool

from services.storage_service import load_game_session, save_game_session
from utils.code_utils import post_process_game_code

VIEW_MAX_LINES = 400
EDIT_CONTEXT_LINES = 3


@dataclass
class GameArtifact:
    code: str = ""
    version: int = 0


@dataclass
class GameContext:
    """Whose game the tools edit, and the artifact as it stands."""
    user_id: str
    scope: str
    unit_id: str
    artifact: GameArtifact = field(default_factory=GameArtifact)

    def save(self, code: str) -> None:
        self.artifact.code = code
        self.artifact.version += 1
        session = load_game_session(self.user_id, self.scope, self.unit_id)
        session.update(code=code, version=self.artifact.version)
        save_game_session(self.user_id, self.scope, self.unit_id, session)


def numbered(code: str, start: int = 1, end: int = 0) -> str:
    """Lines start..end (1-based, inclusive; 0 for the last) prefixed with their numbers."""
    lines = code.split("\n")
    end = min(end or len(lines), len(lines))
    width = len(str(end))
    return "\n".join(f"{n:>{width}} | {lines[n - 1]}" for n in range(start, end + 1))


@tool
def view_game(runtime: ToolRuntime[GameContext], start_line: int = 1, end_line: int = 0) -> str:
    """Show the game code with line numbers, from start_line to end_line (0 for the end)."""
    code = runtime.context.artifact.code
    if not code:
        return "The game is empty. Write it with write_game."
    total = code.count("\n") + 1
    if not 1 <= start_line <= total:
        return f"start_line {start_line} is outside the game, which has {total} lines (1-{total})."
    wanted = min(end_line or total, total)
    end = min(wanted, start_line + VIEW_MAX_LINES - 1)
    out = f"Lines {start_line}-{end} of {total} (version {runtime.context.artifact.version}):\n"
    out += numbered(code, start_line, end)
    if end < wanted:
        out += f"\n[Continues: view_game(start_line={end + 1})]"
    return out


@tool
def write_game(code: str, runtime: ToolRuntime[GameContext]) -> str:
    """Replace the whole game with code: the body of the Game function, ending in
    `return React.createElement(...)`. To fix part of an existing game, use edit_game."""
    code = post_process_game_code(code)
    if not code:
        return "The code is empty; nothing was written."
    runtime.context.save(code)
    return f"Wrote the game: {code.count(chr(10)) + 1} lines (version {runtime.context.artifact.version})."


@tool
def edit_game(old_text: str, new_text: str, runtime: ToolRuntime[GameContext]) -> str:
    """Replace old_text, which must appear exactly once in the game, with new_text.
    Copy old_text exactly (without line numbers), with enough lines to make it unique."""
    code = runtime.context.artifact.code
    if not old_text:
        return "old_text is empty. Copy the exact text to replace from view_game."
    count = code.count(old_text)
    if count == 0:
        return "old_text was not found in the game. Check it against view_game, character for character."
    if count > 1:
        return f"old_text appears {count} times in the game. Include more surrounding lines to pick one."
    at = code.index(old_text)
    runtime.context.save(code[:at] + new_text + code[at + len(old_text):])

    first = code.count("\n", 0, at) + 1
    last = first + new_text.count("\n")
    shown = numbered(runtime.context.artifact.code, max(1, first - EDIT_CONTEXT_LINES), last + EDIT_CONTEXT_LINES)
    return f"Edited lines {first}-{last} (version {runtime.context.artifact.version}). Now:\n{shown}"


GAME_TOOLS = [view_game, write_game, edit_game]
