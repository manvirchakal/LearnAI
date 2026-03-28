"""
Learning profile service — save/load VARK profiles.
Claude description generation is handled by agents/content_agent.py.
"""
import logging

from core.llm import invoke_llm
from services.storage_service import save_profile, load_profile, profile_exists
from utils.prompt_utils import build_learning_profile_prompt

logger = logging.getLogger(__name__)


def generate_profile_description(answers: dict) -> str:
    """Generate a paragraph-long VARK learning profile description using Claude."""
    prompt = build_learning_profile_prompt(answers)
    try:
        return invoke_llm(prompt, max_tokens=300)
    except Exception as e:
        logger.error(f"Error generating profile description: {e}")
        return "Learning profile description unavailable."


def save_learning_profile(user_id: str, answers: dict) -> dict:
    description = generate_profile_description(answers)
    profile = {"answers": answers, "description": description}
    save_profile(user_id, profile)
    return {"message": "Learning profile saved successfully", "description": description}


def get_learning_profile(user_id: str) -> str:
    """Return the learning profile description string, or a fallback."""
    if not user_id:
        return "Learning profile not available."
    try:
        data = load_profile(user_id)
        return data.get("description", "Learning profile not available.")
    except FileNotFoundError:
        return "Learning profile not available."
    except Exception as e:
        logger.error(f"Error fetching learning profile for {user_id}: {e}")
        return "Learning profile not available."


def get_full_learning_profile(user_id: str) -> dict:
    """Return the full profile dict, or empty dict if not found."""
    try:
        return load_profile(user_id)
    except FileNotFoundError:
        return {}
