// Renders LLM-generated game code inside an origin-isolated iframe — the
// real security fix for what DynamicGameComponent.js used to do: splice
// raw model output into `new Function(...)` executed in the app's own
// origin, with full access to cookies, the parent DOM, and credentialed
// fetch. sandbox="allow-scripts" WITHOUT allow-same-origin gives the frame
// an opaque origin instead: no cookies, no localStorage, no parent DOM, no
// same-origin fetch. The in-shell CSP (default-src 'none') blocks network
// egress on top of that. The server-side AST deny-list
// (services/generation/game_validator.py) is defense in depth behind this,
// not the other way around.
//
// No real React inside the frame — bundling a real UMD build into a
// srcdoc string is its own yak-shave, and the generated code only ever
// calls React.createElement/useState/useEffect (see game_code.j2), so a
// minimal hand-rolled implementation of exactly those three is enough and
// keeps the whole shell self-contained with zero network access.
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Box } from '@mui/material';

const SHELL_SCRIPT = `
(function () {
  'use strict';

  var hooks = [];
  var hookIndex = 0;
  var rootEl = document.getElementById('root');
  var rerenderQueued = false;

  function createElement(type, props) {
    var children = [];
    for (var i = 2; i < arguments.length; i++) {
      var child = arguments[i];
      if (Array.isArray(child)) {
        children = children.concat(child);
      } else {
        children.push(child);
      }
    }
    return { type: type, props: props || {}, children: children.filter(function (c) {
      return c !== null && c !== undefined && c !== false;
    }) };
  }

  function buildDom(node) {
    if (typeof node === 'string' || typeof node === 'number') {
      return document.createTextNode(String(node));
    }
    var el = document.createElement(node.type);
    var props = node.props || {};
    Object.keys(props).forEach(function (key) {
      var value = props[key];
      if (key === 'style' && typeof value === 'object') {
        Object.assign(el.style, value);
      } else if (key.indexOf('on') === 0 && typeof value === 'function') {
        el.addEventListener(key.slice(2).toLowerCase(), value);
      } else if (key === 'className') {
        el.setAttribute('class', value);
      } else if (key === 'value' && 'value' in el) {
        el.value = value;
      } else if (value !== false && value !== null && value !== undefined) {
        el.setAttribute(key, value);
      }
    });
    (node.children || []).forEach(function (child) {
      el.appendChild(buildDom(child));
    });
    return el;
  }

  function scheduleRerender() {
    if (rerenderQueued) return;
    rerenderQueued = true;
    queueMicrotask(function () {
      rerenderQueued = false;
      doRender();
    });
  }

  function useState_(initial) {
    var i = hookIndex++;
    if (!(i in hooks)) {
      hooks[i] = { value: typeof initial === 'function' ? initial() : initial };
    }
    var slot = hooks[i];
    function setState(next) {
      slot.value = typeof next === 'function' ? next(slot.value) : next;
      scheduleRerender();
    }
    return [slot.value, setState];
  }

  function useEffect_(effect, deps) {
    var i = hookIndex++;
    var prev = hooks[i];
    var changed = !prev || !deps || !prev.deps ||
      deps.length !== prev.deps.length ||
      deps.some(function (d, idx) { return d !== prev.deps[idx]; });
    if (changed) {
      if (prev && typeof prev.cleanup === 'function') prev.cleanup();
      var deferred = { deps: deps, cleanup: undefined };
      hooks[i] = deferred;
      queueMicrotask(function () {
        deferred.cleanup = effect();
      });
    } else {
      hooks[i] = prev;
    }
  }

  var keyDownHandlers = [];
  document.addEventListener('keydown', function (e) {
    keyDownHandlers.forEach(function (h) { h(e); });
  });
  function onKeyDown(handler) {
    keyDownHandlers.push(handler);
    return function unsubscribe() {
      var idx = keyDownHandlers.indexOf(handler);
      if (idx !== -1) keyDownHandlers.splice(idx, 1);
    };
  }

  function reportComplete(score) {
    var clamped = Math.max(0, Math.min(1, Number(score)));
    if (Number.isNaN(clamped)) return;
    parent.postMessage({ type: 'learnai:game-complete', score: clamped }, '*');
  }

  function reportError(message) {
    parent.postMessage({ type: 'learnai:game-error', message: String(message) }, '*');
  }

  window.addEventListener('error', function (e) {
    reportError(e.message || 'Unknown error');
  });

  function doRender() {
    hookIndex = 0;
    try {
      var vnode = window.__gameFn(
        { createElement: createElement },
        useState_,
        useEffect_,
        reportComplete,
        onKeyDown
      );
      rootEl.innerHTML = '';
      rootEl.appendChild(buildDom(vnode));
    } catch (err) {
      reportError(err && err.message ? err.message : String(err));
    }
  }

  try {
    window.__gameFn = new Function('React', 'useState', 'useEffect', 'reportComplete', 'onKeyDown', __GAME_CODE__);
    doRender();
  } catch (err) {
    reportError(err && err.message ? err.message : String(err));
  }
})();
`;

function buildSrcDoc(javascript) {
  const script = SHELL_SCRIPT.replace('__GAME_CODE__', JSON.stringify(javascript));
  return `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'">
<style>
  html, body { margin: 0; padding: 0; height: 100%; font-family: system-ui, sans-serif; }
  #root { width: 100%; height: 100%; box-sizing: border-box; padding: 12px; }
</style>
</head>
<body>
<div id="root"></div>
<script>${script}</script>
</body>
</html>`;
}

const GameFrame = ({ javascript, onComplete }) => {
  const [error, setError] = useState(null);
  const iframeRef = useRef(null);
  const srcDoc = useMemo(() => buildSrcDoc(javascript), [javascript]);

  useEffect(() => {
    const onMessage = (event) => {
      if (event.source !== iframeRef.current?.contentWindow) return;
      const data = event.data;
      if (!data || typeof data !== 'object') return;
      if (data.type === 'learnai:game-complete') {
        onComplete?.(data.score);
      } else if (data.type === 'learnai:game-error') {
        setError(data.message);
      }
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [onComplete]);

  return (
    <Box>
      {error && (
        <Alert severity="error" sx={{ mb: 1 }}>
          The game hit an error while running: {error}
        </Alert>
      )}
      <iframe
        ref={iframeRef}
        title="Generated game"
        srcDoc={srcDoc}
        sandbox="allow-scripts"
        style={{ width: '100%', height: 480, border: '1px solid #ddd', borderRadius: 4 }}
      />
    </Box>
  );
};

export default GameFrame;
