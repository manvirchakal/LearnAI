"""
LangGraph content generation agent.
Orchestrates: narrative → game_idea → game_code → validate → diagrams → save
"""
import logging
from typing import Any

from langgraph.graph import StateGraph, END

from agents.base import ContentState
from core.llm import invoke_llm
from services.profile_service import get_learning_profile
from services.rag_service import retrieve_context
from services.storage_service import save_narrative, load_narrative
from utils.prompt_utils import build_narrative_prompt, build_game_idea_prompt, format_content_for_prompt
from utils.code_utils import post_process_game_code, validate_js_syntax, GAME_CODE_SYSTEM_PROMPT
from utils.diagram_utils import extract_mermaid_blocks, post_process_mermaid, DIAGRAM_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_CODE_RETRIES = 2


# ── Nodes ─────────────────────────────────────────────────────────────────────

def node_load_cached(state: ContentState) -> ContentState:
    """Skip generation if a cached narrative exists and force_regenerate is False."""
    if state["force_regenerate"]:
        return state
    cached = load_narrative(state["user_id"], state["file_id"], state["section_name"], "false")
    if cached and cached.get("narrative"):
        return {
            **state,
            "narrative": cached.get("narrative", ""),
            "game_idea": cached.get("game_idea", ""),
            "game_code": cached.get("game_code", ""),
            "diagrams": cached.get("diagrams", []),
        }
    return state


def node_retrieve_rag(state: ContentState) -> ContentState:
    context = retrieve_context(state["user_id"], state["section_text"][:2000], file_id=state["file_id"])
    return {**state, "rag_context": context}


def node_generate_narrative(state: ContentState) -> ContentState:
    prompt = build_narrative_prompt(state["section_text"], state["learning_profile"], state["rag_context"])
    try:
        narrative = invoke_llm(prompt, max_tokens=8192)
        return {**state, "narrative": narrative}
    except Exception as e:
        logger.error(f"Narrative generation failed: {e}")
        return {**state, "error": str(e), "narrative": ""}


def node_generate_game_idea(state: ContentState) -> ContentState:
    prompt = build_game_idea_prompt(state["section_text"], state["learning_profile"])
    try:
        game_idea = invoke_llm(prompt, max_tokens=4096)
        return {**state, "game_idea": game_idea}
    except Exception as e:
        logger.error(f"Game idea generation failed: {e}")
        return {**state, "game_idea": ""}


def node_generate_game_code(state: ContentState) -> ContentState:
    prompt = GAME_CODE_SYSTEM_PROMPT.format(game_idea=state["game_idea"])
    try:
        raw = invoke_llm(prompt, max_tokens=3000)
        code = post_process_game_code(raw)
        return {**state, "game_code": code, "code_valid": False}
    except Exception as e:
        logger.error(f"Game code generation failed: {e}")
        return {**state, "game_code": "", "code_valid": False}


def node_validate_game_code(state: ContentState) -> ContentState:
    valid = validate_js_syntax(state["game_code"]) if state["game_code"] else False
    return {**state, "code_valid": valid}


def node_generate_diagrams(state: ContentState) -> ContentState:
    prompt = (
        f"{DIAGRAM_SYSTEM_PROMPT}\n\nPrimary Content:\n{state['section_text']}\n\n"
        f"Generated Summary:\n{state['narrative']}\n\nUser Profile:\n{state['learning_profile']}"
    )
    try:
        response = invoke_llm(prompt, max_tokens=4096)
        raw = extract_mermaid_blocks(response)
        diagrams = [post_process_mermaid(d) for d in raw]
        return {**state, "diagrams": diagrams}
    except Exception as e:
        logger.error(f"Diagram generation failed: {e}")
        return {**state, "diagrams": []}


def node_save_results(state: ContentState) -> ContentState:
    save_narrative(
        state["user_id"], state["file_id"], state["section_name"], "false",
        {"narrative": state["narrative"], "game_idea": state["game_idea"],
         "game_code": state["game_code"], "diagrams": state["diagrams"]},
    )
    return state


# ── Conditional edges ─────────────────────────────────────────────────────────

def should_skip_generation(state: ContentState) -> str:
    """If narrative already populated from cache, skip to save."""
    if state.get("narrative") and not state["force_regenerate"]:
        return "save"
    return "rag"


def should_retry_code(state: ContentState) -> str:
    if state.get("code_valid"):
        return "diagrams"
    retries = state.get("retries", 0)
    if retries < MAX_CODE_RETRIES:
        return "retry"
    return "diagrams"  # give up after max retries


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
    g.add_conditional_edges("load_cached", should_skip_generation, {"save": "save", "rag": "rag"})
    g.add_edge("rag", "narrative")
    g.add_edge("narrative", "game_idea")
    g.add_edge("game_idea", "game_code")
    g.add_edge("game_code", "validate_code")
    g.add_conditional_edges(
        "validate_code",
        should_retry_code,
        {"diagrams": "diagrams", "retry": "game_code"},
    )
    g.add_edge("diagrams", "save")
    g.add_edge("save", END)

    return g.compile()


content_graph = build_content_graph()


def run_content_agent(
    section_text: str,
    user_id: str,
    file_id: str,
    section_name: str,
    force_regenerate: bool = False,
) -> dict:
    """Run the content generation graph and return the result dict."""
    learning_profile = get_learning_profile(user_id)
    initial_state: ContentState = {
        "section_text": section_text,
        "user_id": user_id,
        "file_id": file_id,
        "section_name": section_name,
        "learning_profile": learning_profile,
        "force_regenerate": force_regenerate,
        "rag_context": "",
        "narrative": "",
        "game_idea": "",
        "game_code": "",
        "diagrams": [],
        "code_valid": False,
        "retries": 0,
        "error": None,
    }
    result = content_graph.invoke(initial_state)
    return {
        "narrative": result["narrative"],
        "game_idea": result["game_idea"],
        "game_code": result["game_code"],
        "diagrams": result["diagrams"],
    }
