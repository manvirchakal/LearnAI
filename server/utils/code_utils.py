"""
JavaScript game code validation and post-processing.
"""
import logging
import re

logger = logging.getLogger(__name__)

GAME_CODE_SYSTEM_PROMPT = """Create a fully functional React component for the following game idea that integrates concepts from multiple learning materials:

{game_idea}

The component will be rendered within a DynamicGameComponent via:
  const ComponentFunction = new Function('React', 'useState', 'useEffect', 'MathJax', `return function Game() {{ ... }}`);

Requirements:
1. Use React hooks (useState, useEffect, useRef, useCallback) without React. prefix
2. Use React.createElement for all element creation (no JSX)
3. Return a single root element (usually a div) containing all other elements
4. Ensure all variables and functions are properly declared
5. Do not use any external libraries or components not provided
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


def validate_js_syntax(code: str) -> bool:
    """Validate JavaScript syntax using esprima."""
    try:
        import esprima
        esprima.parseScript(code)
        return True
    except Exception as e:
        logger.warning(f"JS syntax error: {e}")
        return False


def post_process_game_code(code: str) -> str:
    """Clean up Claude-generated game code."""
    # Strip markdown code fences if present
    code = re.sub(r"^```(?:javascript|js)?\n?", "", code, flags=re.MULTILINE)
    code = re.sub(r"\n?```$", "", code, flags=re.MULTILINE)

    # Remove wrapper function artifacts
    code = re.sub(r"^return\s*function\s*\w*\s*\(\)\s*{", "", code)
    code = re.sub(r"}\s*$", "", code)

    # Fix MathJax.Node → MathJax
    code = code.replace("React.createElement(MathJax.Node,", "React.createElement(MathJax,")

    # Fix arrow function spacing
    code = re.sub(r"(\w+)\s*=>\s*{", r"\1 => {", code)

    return code.strip()
