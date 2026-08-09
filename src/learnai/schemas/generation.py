"""Generated study artifacts: game idea/code and diagrams. Narrative has no
schema here — it's plain prose streamed to the client (see
``services/llm/client.py``'s ``stream()``), not structured output.

Structured output (``LLMClient.structured()``) replaces the old
``server/main.py``'s bare ``json.loads`` on raw model text (no fence-
stripping, died on any preamble — ``:709``) and its regex Mermaid scrape
(``:1922``, extracting ```` ```mermaid ```` fences from free text).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

GameControls = Literal["arrow_keys", "click", "type_answer", "drag_and_drop", "none"]


class GameIdea(BaseModel):
    title: str
    description: str
    controls: GameControls
    mechanics: str  # the core gameplay loop — feeds the game_code prompt directly


class GameCode(BaseModel):
    instructions: str  # shown to the player: how to play, and how it relates to the material
    javascript: str
    """A function *body* — no wrapper declaration, no imports. Executed as

        new Function('React', 'useState', 'useEffect', 'reportComplete', 'onKeyDown', javascript)

    inside the sandboxed iframe shell (see the frontend's ``GameFrame``).
    Must return a ``React.createElement`` tree and may call
    ``reportComplete(score)`` (a number 0-1) when the player finishes.
    ``onKeyDown(handler)`` is how keyboard-controlled games read input —
    the code never references ``window``/``document`` directly (both are
    rejected by ``services/generation/game_validator``), so this is the
    only path to keyboard events.
    """


class Diagram(BaseModel):
    title: str
    mermaid: str


class DiagramSet(BaseModel):
    diagrams: list[Diagram] = Field(default_factory=list)
