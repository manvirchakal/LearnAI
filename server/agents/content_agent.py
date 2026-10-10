"""
LangGraph content agent — generates personalized study materials.

Full graph:
    load_cached ─┬─(hit)──────────────────────────────────────────────────▶ END
                 └─(miss)▶ rag ▶ narrative ▶ game_idea ▶ game_code ▶ diagrams ▶ save ▶ END

game_code is a LangChain ReAct agent (create_agent) that builds the game as a
code artifact with GAME_TOOLS (agents/game_tools.py): it writes a first draft,
then makes targeted edits. Its conversation and the artifact are kept per unit
(the game session), so it can pick up where it left off.

The game is checked where it runs, in the student's browser. When it breaks
(at the start or mid-game), the error comes back through the game graph, which
enters straight at game_code: the agent continues its conversation with the
error and fixes the artifact with edits.

Game graph (a new game for an existing unit, or a fix to the current one):
    ┬─(fix)────────────────▶ game_code ▶ save ▶ END
    └─(new)▶ game_idea ────▶ game_code
"""
import logging
from typing import AsyncIterator, List, Optional, Tuple

from langchain.agents import create_agent
from langchain_core.messages import (BaseMessage, HumanMessage, SystemMessage, messages_from_dict,
                                     messages_to_dict)
from langgraph.graph import END, StateGraph

import core.llm
from agents.base import ContentState
from agents.game_tools import GAME_TOOLS, GameArtifact, GameContext
from core.llm import invoke_llm, message_text
from services.profile_service import get_learning_profile
from services.rag_service import retrieve_context
from services.storage_service import (load_game_session, load_study_materials, save_game_session,
                                      save_study_materials)
from utils.code_utils import GAME_AGENT_PROMPT, GAME_RESUME_PROMPT, GAME_TASK_PROMPT, format_game_error
from utils.diagram_utils import DIAGRAM_SYSTEM_PROMPT, extract_mermaid_blocks, post_process_mermaid
from utils.prompt_utils import build_game_idea_prompt, build_narrative_prompt, clip_source

logger = logging.getLogger(__name__)

RESULT_KEYS = ("narrative", "game_idea", "game_code", "diagrams", "game_version")
GAME_MAX_TOKENS = 8192      # write_game carries the whole game as its argument
GAME_RECURSION_LIMIT = 40   # graph steps per agent run: about 20 tool calls
HISTORY_BUDGET_CHARS = 120_000  # a longer game conversation is restarted from the artifact


_DEFAULTS = {"diagrams": [], "game_version": 0}


def _materials(stored: dict) -> dict:
    """Study materials from storage, with defaults for keys older saves lack."""
    return {k: stored.get(k, _DEFAULTS.get(k, "")) for k in RESULT_KEYS}


# ── Nodes ─────────────────────────────────────────────────────────────────────

def node_load_cached(state: ContentState) -> dict:
    if state["force_regenerate"]:
        return {}
    cached = load_study_materials(state["user_id"], state["scope"], state["unit_id"])
    if cached.get("narrative"):
        return {"cached": True, **_materials(cached)}
    return {}


def node_retrieve_rag(state: ContentState) -> dict:
    context = retrieve_context(state["user_id"], state["source_text"][:2000], file_id=state["rag_file_id"])
    return {"rag_context": context}


def node_generate_narrative(state: ContentState) -> dict:
    prompt = build_narrative_prompt(state["source_text"], state["learning_profile"], state["rag_context"])
    return {"narrative": invoke_llm(prompt, max_tokens=8192)}


def node_generate_game_idea(state: ContentState) -> dict:
    if state.get("game_idea"):
        return {}
    try:
        return {"game_idea": invoke_llm(build_game_idea_prompt(state["source_text"], state["learning_profile"]),
                                        max_tokens=4096)}
    except Exception as e:
        logger.error(f"Game idea generation failed: {e}")
        return {"game_idea": ""}


def build_game_agent():
    return create_agent(core.llm.get_llm(max_tokens=GAME_MAX_TOKENS), tools=GAME_TOOLS,
                        context_schema=GameContext, name="game_coder")


def _history_size(messages: List[BaseMessage]) -> int:
    return sum(len(str(m.content)) + len(str(getattr(m, "tool_calls", ""))) for m in messages)


def _game_messages(state: ContentState, session: dict) -> List[BaseMessage]:
    """The conversation to run the game agent on: a new game's task, or the
    saved conversation continued with the error to fix."""
    system = SystemMessage(content=GAME_AGENT_PROMPT)
    if not state.get("game_error"):
        return [system, HumanMessage(content=GAME_TASK_PROMPT.format(game_idea=state["game_idea"]))]
    history = messages_from_dict(session.get("messages", []))
    if not history or _history_size(history) > HISTORY_BUDGET_CHARS:
        history = [system, HumanMessage(content=GAME_RESUME_PROMPT.format(game_idea=state["game_idea"]))]
    return [*history, HumanMessage(content=state["game_error"])]


def node_generate_game_code(state: ContentState) -> dict:
    if not state.get("game_idea"):
        return {"game_code": "", "game_messages": []}
    key = (state["user_id"], state["scope"], state["unit_id"])
    session = load_game_session(*key)
    messages = _game_messages(state, session)
    # Versions only go up, across new games too, so a stale error report never matches
    version = max(state["game_version"], session.get("version", 0))
    artifact = GameArtifact(state["game_code"] if state.get("game_error") else "", version)
    if not state.get("game_error"):
        save_game_session(*key, {"code": "", "version": version, "messages": []})

    try:
        result = build_game_agent().invoke({"messages": messages}, context=GameContext(*key, artifact),
                                           config={"recursion_limit": GAME_RECURSION_LIMIT})
        messages = result["messages"]
    except Exception as e:
        # Whatever the agent wrote before failing is already in the artifact
        logger.error(f"Game agent failed: {e}")

    save_game_session(*key, {"code": artifact.code, "version": artifact.version,
                             "messages": messages_to_dict(messages)})
    return {"game_code": artifact.code, "game_version": artifact.version, "game_messages": messages}


def node_generate_diagrams(state: ContentState) -> dict:
    prompt = (
        f"{DIAGRAM_SYSTEM_PROMPT}\n\nPrimary Content:\n{state['source_text']}\n\n"
        f"Generated Summary:\n{state['narrative']}\n\nUser Profile:\n{state['learning_profile']}"
    )
    try:
        response = invoke_llm(prompt, max_tokens=4096)
        return {"diagrams": [post_process_mermaid(d) for d in extract_mermaid_blocks(response)]}
    except Exception as e:
        logger.error(f"Diagram generation failed: {e}")
        return {"diagrams": []}


def node_save_results(state: ContentState) -> dict:
    save_study_materials(state["user_id"], state["scope"], state["unit_id"],
                         {k: state[k] for k in RESULT_KEYS})
    return {}


# ── Conditional edges ─────────────────────────────────────────────────────────

def route_after_cache(state: ContentState) -> str:
    return "hit" if state.get("cached") else "miss"


def route_game_entry(state: ContentState) -> str:
    return "fix" if state.get("game_error") else "new"


# ── Graph assembly ────────────────────────────────────────────────────────────

def build_content_graph():
    g = StateGraph(ContentState)
    g.add_node("load_cached", node_load_cached)
    g.add_node("rag", node_retrieve_rag)
    g.add_node("narrative", node_generate_narrative)
    g.add_node("game_idea", node_generate_game_idea)
    g.add_node("game_code", node_generate_game_code)
    g.add_node("diagrams", node_generate_diagrams)
    g.add_node("save", node_save_results)

    g.set_entry_point("load_cached")
    g.add_conditional_edges("load_cached", route_after_cache, {"hit": END, "miss": "rag"})
    g.add_edge("rag", "narrative")
    g.add_edge("narrative", "game_idea")
    g.add_edge("game_idea", "game_code")
    g.add_edge("game_code", "diagrams")
    g.add_edge("diagrams", "save")
    g.add_edge("save", END)
    return g.compile()


def build_game_graph():
    g = StateGraph(ContentState)
    g.add_node("game_idea", node_generate_game_idea)
    g.add_node("game_code", node_generate_game_code)
    g.add_node("save", node_save_results)

    g.set_conditional_entry_point(route_game_entry, {"fix": "game_code", "new": "game_idea"})
    g.add_edge("game_idea", "game_code")
    g.add_edge("game_code", "save")
    g.add_edge("save", END)
    return g.compile()


content_graph = build_content_graph()
game_graph = build_game_graph()


# ── Entry points ──────────────────────────────────────────────────────────────

def _initial_state(source_text: str, user_id: str, scope: str, unit_id: str,
                   rag_file_id: Optional[str], force_regenerate: bool) -> ContentState:
    return {
        "source_text": clip_source(source_text),
        "user_id": user_id,
        "scope": scope,
        "unit_id": unit_id,
        "rag_file_id": rag_file_id,
        "learning_profile": get_learning_profile(user_id),
        "force_regenerate": force_regenerate,
        "cached": False,
        "rag_context": "",
        "narrative": "",
        "game_idea": "",
        "game_code": "",
        "diagrams": [],
        "game_version": 0,
        "game_messages": [],
        "game_error": None,
        "error": None,
    }


def load_cached_materials(user_id: str, scope: str, unit_id: str) -> dict:
    """Cached study materials for a unit, or {} — no generation."""
    cached = load_study_materials(user_id, scope, unit_id)
    return _materials(cached) if cached.get("narrative") else {}


def run_content_agent(source_text: str, user_id: str, scope: str, unit_id: str,
                      rag_file_id: Optional[str] = None, force_regenerate: bool = False) -> dict:
    """Return cached study materials for a unit, generating them on a miss."""
    result = content_graph.invoke(
        _initial_state(source_text, user_id, scope, unit_id, rag_file_id, force_regenerate)
    )
    return {k: result[k] for k in RESULT_KEYS}


async def stream_content_agent(source_text: str, user_id: str, scope: str, unit_id: str,
                               rag_file_id: Optional[str] = None,
                               force_regenerate: bool = False) -> AsyncIterator[Tuple[str, object]]:
    """
    Run the content graph, yielding UI events as they happen:
        ("token", str)   narrative text as the model writes it
        ("stage", str)   a graph node finished (load_cached, rag, narrative, game_idea, ...)
        ("done", dict)   final study materials (also when served from cache)
    """
    state = _initial_state(source_text, user_id, scope, unit_id, rag_file_id, force_regenerate)
    async for mode, chunk in content_graph.astream(state, stream_mode=["messages", "updates"]):
        if mode == "messages":
            message, meta = chunk
            if meta.get("langgraph_node") == "narrative":
                token = message_text(message)
                if token:
                    yield "token", token
        else:
            for node in chunk:
                yield "stage", node

    materials = load_cached_materials(user_id, scope, unit_id)
    if not materials:
        raise RuntimeError("Generation finished without producing study materials")
    yield "done", materials


def run_game_agent(source_text: str, user_id: str, scope: str, unit_id: str,
                   new_idea: bool = False) -> dict:
    """Regenerate only the game for a unit whose materials already exist.
    Returns {game_code, game_version}."""
    cached = load_study_materials(user_id, scope, unit_id)
    if not cached.get("narrative"):
        raise LookupError("Generate study materials before regenerating the game")
    state = _initial_state(source_text, user_id, scope, unit_id, None, True)
    state.update(_materials(cached))
    state["game_code"] = ""
    if new_idea:
        state["game_idea"] = ""
    result = game_graph.invoke(state)
    return {"game_code": result["game_code"], "game_version": result["game_version"]}


def run_game_fix(user_id: str, scope: str, unit_id: str, error: str, version: int,
                 line: Optional[int] = None, phase: Optional[str] = None, stack: Optional[str] = None) -> dict:
    """Fix the unit's game after the browser hit an error playing version `version`
    of it. A report about an older version is answered with the current game,
    which has had its own fixes since. Returns {game_code, game_version}."""
    cached = load_study_materials(user_id, scope, unit_id)
    if not cached.get("game_code"):
        raise LookupError("There is no game to fix")
    materials = _materials(cached)
    if version != materials["game_version"]:
        return {"game_code": materials["game_code"], "game_version": materials["game_version"]}
    state = _initial_state("", user_id, scope, unit_id, None, True)
    state.update(materials)
    state["game_error"] = format_game_error(error, materials["game_code"], line=line, phase=phase, stack=stack)
    result = game_graph.invoke(state)
    return {"game_code": result["game_code"], "game_version": result["game_version"]}
