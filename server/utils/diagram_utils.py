"""
Mermaid diagram post-processing.
"""
import re
import logging
from typing import List

logger = logging.getLogger(__name__)

DIAGRAM_SYSTEM_PROMPT = """Based on the following materials, created summary, and the user's learning profile, create a set of diagrams that illustrate the key concepts.

Strict guidelines for Mermaid syntax:
- Start each diagram with 'graph TD' on its own line
- Use only alphanumeric characters and underscores for node IDs (e.g., A, B, Node1)
- Use square brackets for node labels: [Label text]
- Use only --> for arrows
- Put each node and connection on its own line
- Do not use special characters, mathematical symbols, or subscripts in labels
- Use words instead of symbols (e.g., "First Derivative" instead of "f'(x)")
- Ensure all nodes are connected in a logical flow
- Keep labels short and concise
- Limit each diagram to a maximum of 10 nodes

Example:
```mermaid
graph TD
    A[First Concept] --> B[Second Concept]
    B --> C[Third Concept]
```

Provide 2-3 diagrams in correct Mermaid syntax, each enclosed in ```mermaid and ``` tags."""


def extract_mermaid_blocks(text: str) -> List[str]:
    """Extract all ```mermaid ... ``` blocks from a string."""
    return re.findall(r"```mermaid\n(.*?)\n```", text, re.DOTALL)


def post_process_mermaid(diagram: str) -> str:
    """Normalize and fix a Mermaid diagram string."""
    lines = [line for line in diagram.split("\n") if line.strip()]

    if not lines or lines[0].strip() != "graph TD":
        lines.insert(0, "graph TD")

    processed = []
    for line in lines:
        # Clean node IDs (keep only alphanumeric + underscores)
        line = re.sub(
            r"([A-Za-z0-9_]+)",
            lambda m: re.sub(r"[^A-Za-z0-9_]", "", m.group(1)),
            line,
        )
        # Clean node labels
        line = re.sub(r"\[(.*?)\]", lambda m: f"[{m.group(1).replace('_', ' ')}]", line)
        # Normalize arrows
        line = re.sub(r"-->", " --> ", line)
        processed.append(line)

    result = ["graph TD"] + ["    " + ln.strip() for ln in processed[1:]]
    return "\n".join(result)
