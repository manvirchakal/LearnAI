// Plays a generated game for a moment, the way a student would: render it,
// run a few frames, then click each clickable thing once. Returns the first
// error, phrased for the model to fix, or null. Run by utils/game_check.py.
//
// The game is compiled exactly as client/public/sandbox/game-runtime.js does.
import "./env.js";
import * as React from "react";
import TestRenderer from "react-test-renderer";
import { fakeEvent, fakeNode, tick } from "./env.js";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const SCOPE = ["React", "useState", "useEffect", "useRef", "useCallback", "useMemo", "MathJax"];
const PREFIX = '"use strict";\nreturn function Game() {\n';
const FRAMES = 3;

function MathJax(props) {
  return React.createElement(props.inline ? "span" : "div", null, props.children);
}

function compile(body) {
  const factory = new Function(SCOPE.join(","), PREFIX + body + "\n};");
  return factory(React, React.useState, React.useEffect, React.useRef, React.useCallback, React.useMemo, MathJax);
}

// Line of the game body an error was thrown from: new Function puts two lines
// before the function body, PREFIX two more
const HEADER_LINES = 4;

function locate(error, body) {
  // Game frames read "at Game (eval at compile (...), <anonymous>:LINE:COL)"
  const match = /, <anonymous>:(\d+):\d+\)/.exec((error && error.stack) || "");
  if (!match) return "";
  const line = Number(match[1]) - HEADER_LINES;
  const text = body.split("\n")[line - 1];
  return text === undefined ? "" : `\nAt line ${line}: ${text.trim()}`;
}

function textOf(node) {
  if (typeof node === "string") return node;
  return node.children.map(textOf).join(" ").replace(/\s+/g, " ").trim();
}

function describe(node) {
  const text = textOf(node).slice(0, 40);
  return text ? `the <${node.type}> "${text}"` : `a <${node.type}>`;
}

export function checkGame(body, maxClicks) {
  const uncaught = [];
  // React 19 reports errors thrown while rendering here
  globalThis.reportError = (error) => uncaught.push(error);

  const run = (fn) => {
    React.act(fn);
    if (uncaught.length) throw uncaught[0];
  };

  let step = "compiling the game";
  try {
    const Game = compile(body);
    let renderer;
    step = "rendering the first screen";
    run(() => { renderer = TestRenderer.create(React.createElement(Game), { createNodeMock: fakeNode }); });
    for (let i = 0; i < FRAMES; i++) run(tick);

    const clicked = new Set();
    for (let n = 0; n < maxClicks; n++) {
      const target = renderer.root
        .findAll((node) => typeof node.type === "string" && typeof node.props.onClick === "function")
        .find((node) => !clicked.has(describe(node)));
      if (!target) break;
      const label = describe(target);
      clicked.add(label);
      step = `clicking ${label}`;
      run(() => target.props.onClick(fakeEvent("click")));
      for (let i = 0; i < FRAMES; i++) run(tick);
    }
    return null;
  } catch (error) {
    const message = (error && error.message) || String(error);
    return `Error while ${step}: ${message}${locate(error, body)}`;
  }
}

globalThis.checkGame = checkGame;
globalThis.REACT_VERSION = React.version;
