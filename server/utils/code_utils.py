"""
Game agent prompt, error reports for it, and game code post-processing.

The game is checked where it runs: the sandboxed iframe in the browser reports
compile, render and gameplay errors (client/public/sandbox/game-runtime.js),
and they come back to the game agent as messages (agents/content_agent.py).
"""
import re
from typing import Optional

GAME_AGENT_PROMPT = """You write educational games as React components. The game is a code artifact you build with your tools:
- write_game writes the whole game. Use it once, for the first draft.
- view_game shows the code with line numbers.
- edit_game replaces one exact snippet. Use it for every change after the first draft.

The game runs in the student's browser. If it breaks, at the start or while being played, you get a message with the error and the line it happened on. Then view_game around that line, find the cause and fix it with edit_game; never rewrite the whole game to fix a bug. Fix every place the same mistake occurs.

The component runs inside a sandboxed iframe with no network access, compiled via:
  const factory = new Function('React', 'useState', 'useEffect', 'useRef', 'useCallback', 'useMemo', 'MathJax', `return function Game() { <your code> }`);
Your code is the BODY of the Game function: declare state/handlers, then end with `return React.createElement(...)`.
MathJax is a React component that typesets LaTeX children, e.g. React.createElement(MathJax, null, "\\(x^2\\)").

Requirements:
1. Use React hooks (useState, useEffect, useRef, useCallback) without React. prefix
2. Use React.createElement for all element creation (no JSX)
3. Return a single root element (usually a div) containing all other elements
4. Ensure all variables and functions are properly declared
5. Do not use any external libraries or components not provided; do not fetch, load scripts or use storage
6. The code you write is ONLY JavaScript, without explanations or markdown formatting
7. Do not include 'return function Game() {' at the beginning or '}' at the end
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

When the game is written (or fixed), reply with one short sentence saying what you did."""

GAME_TASK_PROMPT = "Create a fully functional React game for this idea, integrating concepts from the learning materials:\n\n{game_idea}"

# Starts a fresh conversation about a game that already exists (one made before
# game sessions were kept, or whose conversation grew too long to keep)
GAME_RESUME_PROMPT = GAME_TASK_PROMPT + "\n\nThe game is already written; it is in the artifact (view_game)."


def format_game_error(error: str, code: str, line: Optional[int] = None, phase: Optional[str] = None,
                      stack: Optional[str] = None) -> str:
    """An error the browser reported, as the message that asks the agent to fix it."""
    when = {
        "compile": "while compiling",
        "render": "while rendering",
        "runtime": "while being played",
        "promise": "in an unhandled promise rejection",
    }.get(phase or "", "in the browser")
    parts = [f"The game broke {when}:\n{error.strip()}"]
    lines = code.split("\n")
    if line and 0 < line <= len(lines):
        parts.append(f"At line {line}: {lines[line - 1].strip()}")
    if stack and stack.strip():
        parts.append(f"Stack:\n{stack.strip()[:1500]}")
    parts.append("Fix it with targeted edits.")
    return "\n\n".join(parts)


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
