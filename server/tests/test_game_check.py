"""The game check: generated code is played in an embedded V8 with the sandbox's React."""
import json
from pathlib import Path

import pytest

import utils.game_check
from utils.code_utils import find_code_error, post_process_game_code
from utils.game_check import find_game_error, react_version

CLIENT_LOCK = Path(__file__).resolve().parents[2] / "client" / "package-lock.json"

CANVAS_GAME = """const ref = useRef(null);
const [running, setRunning] = useState(false);
const [score, setScore] = useState(0);
useEffect(() => {
  const onResize = () => ref.current && ref.current.getBoundingClientRect();
  window.addEventListener("resize", onResize);
  return () => window.removeEventListener("resize", onResize);
}, []);
useEffect(() => {
  if (!running) return;
  const canvas = ref.current;
  const ctx = canvas.getContext("2d");
  let frame;
  const loop = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#0a0";
    ctx.fillRect(10, 10, 20, 20);
    frame = requestAnimationFrame(loop);
  };
  frame = requestAnimationFrame(loop);
  return () => cancelAnimationFrame(frame);
}, [running]);
return React.createElement("div", { style: { width: "100%" } },
  React.createElement("p", null, "Click start, then score points."),
  React.createElement(MathJax, null, "\\\\(x^2\\\\)"),
  React.createElement("canvas", { ref, onClick: (e) => setScore(score + e.clientX) }),
  React.createElement("button", { onClick: () => setRunning(!running) }, running ? "Stop" : "Start"),
  React.createElement("span", null, `Score: ${score}`));"""


def test_working_game_passes():
    assert find_code_error(CANVAS_GAME) is None


def test_error_after_click_is_described_with_line():
    code = ('const [on, setOn] = useState(false);\n'
            'const start = () => { setOn(true); missing.go(); };\n'
            'return React.createElement("button", {onClick: start}, "Begin");')
    error = find_game_error(code)
    assert error.startswith('Error while clicking the <button> "Begin": missing is not defined')
    assert "At line 2: const start" in error


def test_bad_child_found_on_second_screen():
    code = ('const [on, setOn] = useState(false);\n'
            'if (!on) return React.createElement("button", {onClick: () => setOn(true)}, "Start");\n'
            'const styles = {panel: {padding: 4}};\n'
            'return React.createElement("div", styles.panel, {id: "chloroplast"}, "Light reactions");')
    error = find_game_error(code)
    assert "Objects are not valid as a React child (found: object with keys {id})" in error


def test_undefined_component_is_reported():
    # Used to be patched in post-processing; now the model fixes it from the error
    error = find_code_error('return React.createElement(MathJax.Node, null, "\\\\(x\\\\)");')
    assert "Element type is invalid" in error and "rendering the first screen" in error


def test_syntax_error_points_at_body_line():
    error = find_code_error("const a = 1;\nreturn React.createElement(\n")
    assert error.startswith("Syntax error:")
    assert find_code_error("const a = 1;\nconst = 2;\nreturn null;").endswith("At line 2: const = 2;")


def test_empty_code():
    assert find_code_error("  ") == "The game code is empty."


def test_endless_loop_times_out(monkeypatch):
    monkeypatch.setattr(utils.game_check, "TIMEOUT_SEC", 0.5)
    code = ('const [on, setOn] = useState(false);\n'
            'if (on) { while (true) {} }\n'
            'return React.createElement("button", {onClick: () => setOn(true)}, "Go");')
    assert "did not respond" in find_game_error(code)


def test_post_processing_unwraps_without_rewriting():
    raw = '```javascript\nfunction Game() {\nreturn React.createElement(MathJax.Node, null, "x");\n}\n```'
    assert post_process_game_code(raw) == 'return React.createElement(MathJax.Node, null, "x");'


@pytest.mark.skipif(not CLIENT_LOCK.exists(), reason="client/ not checked out")
def test_checks_with_the_sandbox_react_version():
    lock = json.loads(CLIENT_LOCK.read_text())
    assert react_version() == lock["packages"]["node_modules/react"]["version"], \
        "rebuild server/game_check/bundle.js with the client's React version"
