// Game runtime for the sandboxed iframe (see game.html).
//
// Protocol with the parent (components/game/DynamicGameComponent.tsx):
//   → parent   { type: "ready" }                   runtime loaded
//   ← parent   { type: "run", code }               the BODY of a Game() component
//   → parent   { type: "error", message, phase, line, stack }
//                                                  the first compile, render or runtime error;
//                                                  line is in the game code, stack lists game frames
//   → parent   { type: "resize", height }          content height in px
//
// The game contract (server/utils/code_utils.py) is unchanged: the body is
// compiled with React, the hooks and a MathJax component in scope.
(function () {
  "use strict";
  var React = window.React;
  var h = React.createElement;

  function post(message) {
    window.parent.postMessage(Object.assign({ source: "learnai-game" }, message), "*");
  }

  function describe(err) {
    if (err && err.message) return (err.name && err.name !== "Error" ? err.name + ": " : "") + err.message;
    return String(err);
  }

  // The game is compiled as a named script, so its frames can be told apart in a stack
  var SOURCE = "learnai-game.js";
  var FRAME = /learnai-game\.js:(\d+)(?::(\d+))?/;

  function wrap(body) {
    return '"use strict";\nreturn function Game() {\n' + body + "\n};\n//# sourceURL=" + SOURCE;
  }

  // Script lines before the game code's first line, which differ by browser
  // (new Function adds its own header): found by compiling a probe the same way
  var LINE_OFFSET = (function () {
    try {
      // eslint-disable-next-line no-new-func
      var m = FRAME.exec(new Function(wrap("return new Error().stack;"))()() || "");
      return m ? Number(m[1]) - 1 : null;
    } catch (e) {
      return null;
    }
  })();

  /** A stack frame with its script position turned into a game code line. */
  function gameFrame(frame) {
    return frame.replace(FRAME, function (_, l, c) {
      return "game line " + (Number(l) - LINE_OFFSET) + (c ? ":" + c : "");
    }).trim();
  }

  /** The game's frames of a stack, and the game code line of the first. */
  function gameStack(stack) {
    if (!stack || LINE_OFFSET === null) return { line: undefined, stack: undefined };
    var frames = String(stack).split("\n").filter(function (f) { return FRAME.test(f); });
    if (!frames.length) return { line: undefined, stack: undefined };
    return {
      line: Number(FRAME.exec(frames[0])[1]) - LINE_OFFSET,
      stack: frames.slice(0, 10).map(gameFrame).join("\n"),
    };
  }

  var reported = false;

  function report(phase, err, extraStack) {
    if (reported) return; // the first error is the one to fix; later ones tend to follow from it
    reported = true;
    var where = gameStack(err && err.stack);
    var stack = [where.stack, extraStack && String(extraStack).trim()].filter(Boolean).join("\n");
    post({ type: "error", message: describe(err), phase: phase, line: where.line, stack: stack || undefined });
  }

  /** Typesets its LaTeX children once MathJax has loaded. */
  function MathJax(props) {
    var ref = React.useRef(null);
    var children = props.children;
    React.useEffect(function () {
      var el = ref.current;
      var cancelled = false;
      function typeset() {
        if (cancelled || !el) return;
        var mj = window.MathJax;
        if (mj && mj.typesetPromise) {
          if (mj.typesetClear) mj.typesetClear([el]);
          mj.typesetPromise([el]).catch(function () {});
        } else {
          setTimeout(typeset, 100);
        }
      }
      typeset();
      return function () { cancelled = true; };
    }, [children]);
    return h(props.inline ? "span" : "div", { ref: ref, key: String(children) }, children);
  }

  class Boundary extends React.Component {
    constructor(props) {
      super(props);
      this.state = { failed: false };
    }
    static getDerivedStateFromError() {
      return { failed: true };
    }
    componentDidCatch(error, info) {
      var components = info && info.componentStack && LINE_OFFSET !== null
        ? info.componentStack.split("\n").map(gameFrame).filter(Boolean).join("\n")
        : "";
      report("render", error, components && "Components:\n" + components);
    }
    render() {
      return this.state.failed ? null : this.props.children;
    }
  }

  var SCOPE = ["React", "useState", "useEffect", "useRef", "useCallback", "useMemo", "MathJax"];
  var VALUES = [React, React.useState, React.useEffect, React.useRef, React.useCallback, React.useMemo, MathJax];

  function compile(body) {
    // eslint-disable-next-line no-new-func
    var factory = new Function(SCOPE.join(","), wrap(body));
    var Game = factory.apply(null, VALUES);
    if (typeof Game !== "function") throw new Error("Game code did not produce a component");
    return Game;
  }

  var root = null;
  var started = false;

  function run(code) {
    if (started) return; // one game per frame; the parent remounts the iframe for a new one
    started = true;
    var Game;
    try {
      Game = compile(code);
    } catch (e) {
      report("compile", e);
      return;
    }
    root = window.ReactDOM.createRoot(document.getElementById("root"));
    root.render(h(Boundary, null, h(Game)));
  }

  // Errors outside React's render phase (event handlers, timers, rAF loops)
  window.addEventListener("error", function (e) {
    // "Script error." is a muted error from a script loaded without CORS (MathJax's
    // lazily loaded components); it carries no information and isn't the game's
    if (!e.error && e.message === "Script error.") return;
    report("runtime", e.error || new Error(e.message));
  });
  window.addEventListener("unhandledrejection", function (e) {
    report("promise", e.reason);
  });

  window.addEventListener("message", function (e) {
    if (e.source !== window.parent) return;
    var data = e.data;
    if (data && data.type === "run" && typeof data.code === "string") run(data.code);
  });

  var lastHeight = 0;
  function reportHeight() {
    var height = Math.ceil(document.documentElement.scrollHeight);
    if (height !== lastHeight) {
      lastHeight = height;
      post({ type: "resize", height: height });
    }
  }
  new ResizeObserver(reportHeight).observe(document.body);

  post({ type: "ready" });
})();
