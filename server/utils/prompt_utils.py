"""
Dynamic prompt construction utilities.
"""
from typing import Dict


LEARNING_CATEGORIES = {
    "Visual": [
        "I find it easier to understand new information when it is presented in diagrams, charts, or graphs.",
        "I prefer learning new concepts by observing demonstrations.",
        "I often visualize concepts or problems in my mind to help me solve them.",
        "I use colors, symbols, or drawings when taking notes to help me organize my thoughts.",
        "I remember information better when I see it written down or displayed on a screen",
    ],
    "Auditory": [
        "I learn better when I listen to explanations rather than read them.",
        "I prefer to learn by listening to audio lectures or podcasts.",
        "I remember information better when I hear it spoken aloud.",
        "I use mnemonics or chants to help me memorize information.",
        "I learn best by discussing concepts with others.",
    ],
    "ReadingWriting": [
        "I understand new ideas best when I write them down.",
        "I learn best by reading textbooks or articles.",
        "I use flashcards or mind maps to help me memorize information.",
        "I prefer to learn by reading and writing rather than listening or watching.",
        "I use diagrams or charts to help me understand and remember information.",
    ],
    "Kinesthetic": [
        "I enjoy working with physical models or doing hands-on activities to learn.",
        "I learn best by doing experiments or practical activities.",
        "I use role-playing or simulations to help me understand and apply new concepts.",
        "I prefer to learn by solving real-world problems or puzzles.",
        "I use physical models or manipulatives to help me visualize and understand information.",
    ],
}


def format_content_for_prompt(content: Dict) -> str:
    """Combine multi-source collection content into a single prompt string."""
    parts = []

    if content.get("textbook_content"):
        parts.append("TEXTBOOK SECTIONS:")
        for section in content["textbook_content"]:
            text = section if isinstance(section, str) else section.get("text", "")
            parts.append(f"- {text}")

    if content.get("transcriptions"):
        parts.append("\nLECTURE TRANSCRIPTIONS:")
        for trans in content["transcriptions"]:
            parts.append(f"- {trans}" if isinstance(trans, str) else f"- {trans}")

    if content.get("presentations"):
        parts.append("\nPRESENTATIONS:")
        for pres in content["presentations"]:
            slides = pres.get("slides", []) if isinstance(pres, dict) else []
            for i, slide in enumerate(slides):
                parts.append(f"Slide {i+1}: {slide.get('content', '')}")

    if content.get("notes"):
        parts.append("\nHANDWRITTEN NOTES:")
        for note in content["notes"]:
            text_items = note.get("text_content", []) if isinstance(note, dict) else []
            for item in text_items:
                parts.append(f"- {item.get('text', '')}")

    return "\n".join(parts)


def generate_dynamic_prompt(content: Dict, task: str) -> str:
    base_prompts = {
        "summary": (
            "Generate a comprehensive summary that synthesizes information from multiple learning materials. "
            "Focus on key concepts, relationships between ideas, and important takeaways."
        ),
        "game": (
            "Create an interactive learning game concept that tests understanding of the material. "
            "Include specific questions and scenarios based on the content."
        ),
        "diagrams": (
            "Generate clear, informative diagrams that visualize key concepts and relationships "
            "from the learning materials."
        ),
    }

    prompt_parts = [base_prompts.get(task, "")]

    if content.get("textbook_content"):
        prompt_parts.append(
            "From the textbook sections, incorporate key definitions, concepts, and theoretical frameworks."
        )
    if content.get("transcriptions"):
        prompt_parts.append(
            "From the lecture transcriptions, include practical examples, explanations, and real-world applications."
        )
    if content.get("presentations"):
        prompt_parts.append(
            "From the presentation slides, use the main points, visual concepts, and structured progression."
        )
    if content.get("notes"):
        prompt_parts.append(
            "From the handwritten notes, include additional insights and supplementary examples."
        )

    if task == "summary":
        prompt_parts.append("Create a coherent narrative that flows naturally between different source materials.")
    elif task == "game":
        prompt_parts.append("Design interactions that test understanding across all available materials.")
    elif task == "diagrams":
        prompt_parts.append("Create visualizations that show relationships between concepts from different sources.")

    content_text = format_content_for_prompt(content)
    return "\n\n".join(prompt_parts) + f"\n\nContent to work with:\n\n{content_text}"


def build_learning_profile_prompt(answers: Dict) -> str:
    import json
    return f"""Based on the following questionnaire answers, generate a paragraph-long textual description of the user's learning style.
The answers are organized by learning category (Visual, Auditory, ReadingWriting, Kinesthetic) and represent the user's agreement level (1: Strongly Disagree, 5: Strongly Agree).

Questionnaire:
{json.dumps(LEARNING_CATEGORIES, indent=2)}

Questionnaire answers:
{json.dumps(answers, indent=2)}

Please provide a comprehensive description of the user's learning style, highlighting strengths and preferences. Be informative and tailored to the individual."""


def build_narrative_prompt(section_text: str, learning_profile: str, rag_context: str = "") -> str:
    return f"""You are LearnAI, a GenAI powered learning assistant that adjusts content to the user's learning profile.
Generate an extensive, in-depth summary for the following materials, making sure to cover all key concepts
while incorporating the provided relevant information and tailoring it to the user's learning profile:

Primary Content from Collection:
{section_text}

Additional Relevant Information:
{rag_context}

Learning profile: {learning_profile}

Please create a comprehensive, detailed walkthrough that:
1. Thoroughly explains all key concepts from all materials
2. Provides multiple examples and applications
3. Uses rich analogies and real-world examples
4. Addresses common misconceptions
5. Includes thought-provoking questions
6. Adjusts content to cater to the user's learning profile"""


def build_game_idea_prompt(text: str, learning_profile: str) -> str:
    return f"""Based on the following materials and the user's learning profile, suggest a simple interactive game idea that reinforces the key concepts. The game should:
1. Be implementable in JavaScript
2. Reinforce one or more key concepts from the materials
3. Be engaging and educational for students
4. Not be resource intensive and be able to run on a web browser using React
5. Be tailored to the user's learning style as described in their profile

Primary Content from Collection:
{text}

User's learning profile: {learning_profile}

Now, provide a game idea that integrates concepts from the available materials."""


def build_chat_prompt(
    user_message: str,
    extracted_text: str,
    generated_summary: str,
    rag_context: str,
    learning_profile: str,
) -> str:
    return f"""Here's the user's learning profile: {learning_profile}

You are LearnAI, a GenAI powered learning assistant that adjusts textbook content to the user's learning profile.
The current section content is: {extracted_text[:3000]}
The generated summary of this section is: {generated_summary[:2000]}
Relevant information: {rag_context[:2000]}

Remember the context of the previous messages. Here's the student's latest question:
{user_message}

Provide a helpful, accurate, and concise answer based on the given context and conversation history. Answer but be concise (4-6 sentences)."""
