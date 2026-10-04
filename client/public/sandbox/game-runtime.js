// Game runtime for the sandboxed iframe (see game.html).
//
// Protocol with the parent (components/game/DynamicGameComponent.tsx):
//   → parent   { type: "ready" }                   runtime loaded
//   ← parent   { type: "run", code }               the BODY of a Game() component
//   → parent   { type: "error", message }          compile, render or runtime error
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
    if (err && err.message) return err.message;
    return String(err);
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
    componentDidCatch(error) {
      post({ type: "error", message: describe(error) });
    }
    render() {
      return this.state.failed ? null : this.props.children;
    }
  }

  var SCOPE = ["React", "useState", "useEffect", "useRef", "useCallback", "useMemo", "MathJax"];
  var VALUES = [React, React.useState, React.useEffect, React.useRef, React.useCallback, React.useMemo, MathJax];

  function compile(body) {
    // eslint-disable-next-line no-new-func
    var factory = new Function(SCOPE.join(","), '"use strict";\nreturn function Game() {\n' + body + "\n};");
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
      post({ type: "error", message: describe(e) });
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
    post({ type: "error", message: describe(e.error || e.message) });
  });
  window.addEventListener("unhandledrejection", function (e) {
    post({ type: "error", message: describe(e.reason) });
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
