"""
JavaScript game code validation and post-processing.
"""
import logging
import re
from typing import Optional

import esprima

from utils.game_check import find_game_error

logger = logging.getLogger(__name__)

GAME_CODE_SYSTEM_PROMPT = """Create a fully functional React component for the following game idea that integrates concepts from multiple learning materials:

{game_idea}

The component runs inside a sandboxed iframe with no network access, compiled via:
  const factory = new Function('React', 'useState', 'useEffect', 'useRef', 'useCallback', 'useMemo', 'MathJax', `return function Game() {{ <your code> }}`);
Your code is the BODY of the Game function: declare state/handlers, then end with `return React.createElement(...)`.
MathJax is a React component that typesets LaTeX children, e.g. React.createElement(MathJax, null, "\\(x^2\\)").

Requirements:
1. Use React hooks (useState, useEffect, useRef, useCallback) without React. prefix
2. Use React.createElement for all element creation (no JSX)
3. Return a single root element (usually a div) containing all other elements
4. Ensure all variables and functions are properly declared
5. Do not use any external libraries or components not provided; do not fetch, load scripts or use storage
6. Provide ONLY the JavaScript code, without any explanations or markdown formatting
7. Do not include 'return function Game() {{' at the beginning or '}}' at the end
8. Use proper JavaScript syntax (no semicolons after blocks or object literals in arrays)
9. Do not use 'function' as a variable name; use 'func' or 'mathFunction' instead
10. Create instructions for the user on how to play the game in the game component
11. Use safe evaluation methods instead of eval()
12. Ensure all variables used in calculations are properly defined and initialized
13. Use try-catch blocks for calculations to handle potential errors gracefully
14. For keyboard input: use useEffect to add/remove event listeners; call e.preventDefault()
15. Add a button to start/restart the game; only capture keyboard input when game is active
16. Use requestAnimationFrame for game loops
17. The background color is white; keep this as the game background
18. Container sizing: use relative units (%, vh, vw); game must auto-scale to its container
19. Add useEffect for window resizing; use getBoundingClientRect() for accurate dimensions

Generate the game code now, no explanations or comments, just the code:"""

# Sent as the next turn of the game code conversation when the code breaks, so
# the model fixes its own game with the original task in view
GAME_CODE_FEEDBACK_PROMPT = """That code breaks when the game is played:

{error}

Fix it and provide the complete corrected code, without any explanations or markdown formatting."""


def wrap_game_body(code: str) -> str:
    """The exact shape the frontend executes (client/public/sandbox/game-runtime.js)."""
    return f"function Game() {{\n{code}\n}}"


def find_code_error(code: str) -> Optional[str]:
    """Why the generated function body won't run as a game, or None if it plays."""
    if not code.strip():
        return "The game code is empty."
    try:
        esprima.parseScript(wrap_game_body(code))
    except esprima.Error as e:
        # The wrapper's first line shifts esprima's line numbers by one
        line = e.lineNumber - 1
        lines = code.split("\n")
        description = re.sub(r"^Line \d+: ", "", e.message)
        if 0 < line <= len(lines):
            return f"Syntax error: {description}\nAt line {line}: {lines[line - 1].strip()}"
        return f"Syntax error: {description}"
    return find_game_error(code)


def post_process_game_code(code: str) -> str:
    """Clean up LLM-generated game code into a bare Game function body."""
    code = code.strip()
    # Strip markdown code fences if present
    code = re.sub(r"^```(?:javascript|jsx?|js)?\s*\n?", "", code)
    code = re.sub(r"\n?```\s*$", "", code).strip()

    # If the model wrapped the body anyway, unwrap it (and only then drop the closing brace)
    wrapper = re.match(r"^(?:return\s+)?function\s*\w*\s*\(\s*\)\s*\{", code)
    if wrapper and code.endswith("}"):
        code = code[wrapper.end():-1].strip()
    return code
