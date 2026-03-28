import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from core.dependencies import get_user_id
from core.llm import stream_llm
from models.ai_outputs import GameIdeaRequest, GenerateNarrativeRequest
from services.collection_service import get_collection_content
from services.profile_service import get_learning_profile
from services.rag_service import retrieve_context
from services.storage_service import save_narrative, load_narrative
from utils.prompt_utils import format_content_for_prompt, build_narrative_prompt, build_game_idea_prompt
from utils.code_utils import post_process_game_code, GAME_CODE_SYSTEM_PROMPT
from utils.diagram_utils import extract_mermaid_blocks, post_process_mermaid, DIAGRAM_SYSTEM_PROMPT
from utils.streaming_utils import text_stream_to_sse, collect_stream
from core.llm import invoke_llm

logger = logging.getLogger(__name__)
router = APIRouter(tags=["content"])


@router.post("/generate-narrative/{collection_id}")
async def generate_narrative_endpoint(
    collection_id: str,
    user_id: str = Depends(get_user_id),
):
    try:
        content = get_collection_content(collection_id, user_id)
        learning_profile = get_learning_profile(user_id)
        content_text = format_content_for_prompt(content)
        rag_context = retrieve_context(user_id, content_text[:2000])

        narrative_prompt = build_narrative_prompt(content_text, learning_profile, rag_context)
        narrative = invoke_llm(narrative_prompt, max_tokens=8192)

        game_prompt = build_game_idea_prompt(content_text, learning_profile)
        game_idea = invoke_llm(game_prompt, max_tokens=4096)

        game_code_prompt = GAME_CODE_SYSTEM_PROMPT.format(game_idea=game_idea)
        raw_code = invoke_llm(game_code_prompt, max_tokens=3000)
        game_code = post_process_game_code(raw_code)

        diagram_prompt = f"{DIAGRAM_SYSTEM_PROMPT}\n\nPrimary Content:\n{content_text}\n\nGenerated Summary:\n{narrative}\n\nUser Profile:\n{learning_profile}"
        diagram_response = invoke_llm(diagram_prompt, max_tokens=4096)
        raw_diagrams = extract_mermaid_blocks(diagram_response)
        diagrams = [post_process_mermaid(d) for d in raw_diagrams]

        return {"narrative": narrative, "game_idea": game_idea, "game_code": game_code, "diagrams": diagrams}

    except Exception as e:
        logger.error(f"Error generating narrative: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-game-code")
async def generate_game_code_endpoint(request: GameIdeaRequest):
    try:
        prompt = GAME_CODE_SYSTEM_PROMPT.format(game_idea=request.game_idea)
        raw = invoke_llm(prompt, max_tokens=3000)
        return {"code": post_process_game_code(raw)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream-narrative/{collection_id}")
async def stream_narrative(
    collection_id: str,
    user_id: str = Depends(get_user_id),
):
    """Streaming SSE endpoint for narrative generation."""
    try:
        content = get_collection_content(collection_id, user_id)
        learning_profile = get_learning_profile(user_id)
        content_text = format_content_for_prompt(content)
        rag_context = retrieve_context(user_id, content_text[:2000])
        prompt = build_narrative_prompt(content_text, learning_profile, rag_context)

        async def _gen():
            async for token in stream_llm(prompt, max_tokens=8192):
                yield token

        return StreamingResponse(
            text_stream_to_sse(_gen()),
            media_type="text/event-stream",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
