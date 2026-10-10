"""
LangGraph content agent — generates personalized study materials.

Full graph:
    load_cached ─┬─(hit)──────────────────────────────────────────────────────▶ END
                 └─(miss)▶ rag ▶ narrative ▶ game_idea ▶ game_code ▶ validate_code
                                                            ▲            │
                                                            └─(retry)────┤
                                                                 diagrams ◀┘ ▶ save ▶ END

validate_code plays the game briefly (utils/game_check.py). A retry continues
the game code conversation with the error, so the model fixes its own game.

Game graph (regenerate just the game for an existing unit):
    game_idea ▶ game_code ▶ validate_code ─(retry)▶ game_code
                                          └──────▶ save ▶ END
"""
import logging
from typing import AsyncIterator, Optional, Tuple

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph

from agents.base import ContentState
from core.llm import invoke_llm, message_text
from services.profile_service import get_learning_profile
from services.rag_service import retrieve_context
from services.storage_service import load_study_materials, save_study_materials
from utils.code_utils import (GAME_CODE_FEEDBACK_PROMPT, GAME_CODE_SYSTEM_PROMPT, find_code_error,
                              post_process_game_code)
from utils.diagram_utils import DIAGRAM_SYSTEM_PROMPT, extract_mermaid_blocks, post_process_mermaid
from utils.prompt_utils import build_game_idea_prompt, build_narrative_prompt, clip_source

logger = logging.getLogger(__name__)

MAX_CODE_RETRIES = 2
RESULT_KEYS = ("narrative", "game_idea", "game_code", "diagrams")


# ── Nodes ─────────────────────────────────────────────────────────────────────

def node_load_cached(state: ContentState) -> dict:
    if state["force_regenerate"]:
        return {}
    cached = load_study_materials(state["user_id"], state["scope"], state["unit_id"])
    if cached.get("narrative"):
        return {"cached": True, **{k: cached.get(k, [] if k == "diagrams" else "") for k in RESULT_KEYS}}
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


def node_generate_game_code(state: ContentState) -> dict:
    if not state.get("game_idea"):
        return {"game_code": "", "game_messages": [], "code_error": None}
    if state.get("code_error") and state.get("game_messages"):
        feedback = GAME_CODE_FEEDBACK_PROMPT.format(error=state["code_error"])
        messages = [*state["game_messages"], HumanMessage(content=feedback)]
    else:
        messages = [HumanMessage(content=GAME_CODE_SYSTEM_PROMPT.format(game_idea=state["game_idea"]))]
    try:
        reply = invoke_llm(messages, max_tokens=4096)
    except Exception as e:
        logger.error(f"Game code generation failed: {e}")
        return {"game_code": "", "game_messages": []}
    return {"game_code": post_process_game_code(reply), "game_messages": [*messages, AIMessage(content=reply)]}


def node_validate_game_code(state: ContentState) -> dict:
    error = find_code_error(state["game_code"])
    if error:
        logger.info(f"Game code attempt {state['retries'] + 1} failed: {error}")
    return {"code_error": error, "retries": state["retries"] + (1 if error else 0)}


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


def route_after_validation(state: ContentState) -> str:
    if not state["code_error"] or not state.get("game_idea"):
        return "done"
    return "retry" if state["retries"] <= MAX_CODE_RETRIES else "done"


# ── Graph assembly ────────────────────────────────────────────────────────────

def build_content_graph():
    g = StateGraph(ContentState)
    g.add_node("load_cached", node_load_cached)
    g.add_node("rag", node_retrieve_rag)
    g.add_node("narrative", node_generate_narrative)
    g.add_node("game_idea", node_generate_game_idea)
    g.add_node("game_code", node_generate_game_code)
    g.add_node("validate_code", node_validate_game_code)
    g.add_node("diagrams", node_generate_diagrams)
    g.add_node("save", node_save_results)

    g.set_entry_point("load_cached")
    g.add_conditional_edges("load_cached", route_after_cache, {"hit": END, "miss": "rag"})
    g.add_edge("rag", "narrative")
    g.add_edge("narrative", "game_idea")
    g.add_edge("game_idea", "game_code")
    g.add_edge("game_code", "validate_code")
    g.add_conditional_edges("validate_code", route_after_validation, {"retry": "game_code", "done": "diagrams"})
    g.add_edge("diagrams", "save")
    g.add_edge("save", END)
    return g.compile()


def build_game_graph():
    g = StateGraph(ContentState)
    g.add_node("game_idea", node_generate_game_idea)
    g.add_node("game_code", node_generate_game_code)
    g.add_node("validate_code", node_validate_game_code)
    g.add_node("save", node_save_results)

    g.set_entry_point("game_idea")
    g.add_edge("game_idea", "game_code")
    g.add_edge("game_code", "validate_code")
    g.add_conditional_edges("validate_code", route_after_validation, {"retry": "game_code", "done": "save"})
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
        "game_messages": [],
        "code_error": None,
        "retries": 0,
        "error": None,
    }


def load_cached_materials(user_id: str, scope: str, unit_id: str) -> dict:
    """Cached study materials for a unit, or {} — no generation."""
    cached = load_study_materials(user_id, scope, unit_id)
    return {k: cached[k] for k in RESULT_KEYS if k in cached} if cached.get("narrative") else {}


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
                   new_idea: bool = False) -> str:
    """Regenerate only the game for a unit whose materials already exist."""
    cached = load_study_materials(user_id, scope, unit_id)
    if not cached.get("narrative"):
        raise LookupError("Generate study materials before regenerating the game")
    state = _initial_state(source_text, user_id, scope, unit_id, None, True)
    state.update({k: cached.get(k, state[k]) for k in RESULT_KEYS})
    state["game_code"] = ""
    if new_idea:
        state["game_idea"] = ""
    return game_graph.invoke(state)["game_code"]
