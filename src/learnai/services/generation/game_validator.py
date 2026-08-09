"""AST deny-list validator for LLM-generated game code.

Defense in depth, not the primary guarantee — the real security boundary
is origin isolation. The frontend's ``GameFrame`` renders generated code
in an iframe with ``sandbox="allow-scripts"`` and no ``allow-same-origin``,
so it has no cookies, no parent DOM, and no same-origin ``fetch``
regardless of what this validator catches or misses. This exists to
reject code with no legitimate reason to touch the network/DOM/eval-
family APIs *before* it ever reaches a browser, and to give a clean
failure instead of a raw stack trace — the old ``server/main.py`` had an
esprima syntax check and a ``post_process_game_code`` regex cleanup, but
neither was ever actually called anywhere.

Deliberately conservative: a bare reference to a denied identifier is
rejected even where it's really a property name rather than a global
reference (``{ window: true }``) — a rare, single-round false positive
here (the repair-then-fail-clean path in ``services/generation/game.py``)
costs far less than a missed real one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import esprima
from esprima.error_handler import Error as EsprimaSyntaxError

# The eval/Function-family sandbox escapes, plus the DOM/network/storage
# surface an educational game has no legitimate reason to touch.
# globalThis/self/top/frames are included alongside window/document/parent
# because any of them reaches the same global object a name-only block on
# just "window" would otherwise leave open.
_DENIED_IDENTIFIERS = frozenset(
    {
        "eval",
        "Function",
        "require",
        "fetch",
        "XMLHttpRequest",
        "WebSocket",
        "document",
        "window",
        "parent",
        "top",
        "frames",
        "self",
        "globalThis",
        "localStorage",
        "sessionStorage",
        "indexedDB",
    }
)

# {}.constructor.constructor('return this')() reaches the Function
# constructor without ever naming "Function" or "eval" directly.
_DENIED_PROPERTIES = frozenset({"constructor", "__proto__"})


@dataclass(frozen=True, slots=True)
class Violation:
    rule: str
    detail: str


def find_violations(code: str) -> list[Violation]:
    """Empty list means the code passed. A syntax error is itself a
    (single) violation rather than a raised exception — callers treat
    "doesn't parse" and "parses but touches something denied" the same
    way: reject and retry/fail clean, not crash."""
    # Parsed as a function body — matching the `new Function('React',
    # 'useState', 'useEffect', 'reportComplete', code)` wrapping this code
    # actually runs under. A bare top-level `return`, which every
    # generated game ends with (see game_code.j2), is otherwise a syntax
    # error: esprima.parseScript treats unwrapped code as a top-level
    # Program, where `return` outside a function is illegal.
    wrapped = f"function __game__() {{\n{code}\n}}"
    try:
        tree = esprima.parseScript(wrapped, options={"tolerant": False})
    except EsprimaSyntaxError as exc:
        return [Violation(rule="syntax_error", detail=str(exc))]

    violations: list[Violation] = []
    _walk(tree.toDict(), violations)
    return violations


def _walk(node: Any, violations: list[Violation]) -> None:
    if isinstance(node, list):
        for item in node:
            _walk(item, violations)
        return
    if not isinstance(node, dict):
        return

    node_type = node.get("type")

    if node_type == "Identifier" and node.get("name") in _DENIED_IDENTIFIERS:
        violations.append(
            Violation(rule="denied_identifier", detail=f"references {node['name']!r}")
        )
    elif node_type == "ImportExpression" or (
        node_type == "CallExpression"
        and isinstance(node.get("callee"), dict)
        and node["callee"].get("type") == "Import"
    ):
        violations.append(Violation(rule="dynamic_import", detail="uses import()"))
    elif node_type == "MemberExpression":
        prop = node.get("property")
        if isinstance(prop, dict):
            name: object = None
            if not node.get("computed") and prop.get("type") == "Identifier":
                name = prop.get("name")
            elif node.get("computed") and prop.get("type") == "Literal":
                name = prop.get("value")
            if name in _DENIED_PROPERTIES:
                violations.append(Violation(rule="denied_property", detail=f"accesses .{name}"))

    for value in node.values():
        _walk(value, violations)
