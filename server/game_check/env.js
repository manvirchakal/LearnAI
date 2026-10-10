// Browser globals that React and generated games expect, for a bare V8 context.
// Imported before React so the scheduler picks up these timers. Timers and
// animation frames only queue; the harness runs them with tick().

const noop = () => {};

/** A value that absorbs any use (call, property, arithmetic) without throwing. */
export function absorb() {
  return new Proxy(function () {}, {
    get(_, key) {
      if (key === Symbol.toPrimitive) return () => 0;
      if (key === Symbol.iterator) return function* () {};
      if (key === "then") return undefined;
      return absorb();
    },
    set: () => true,
    apply: () => absorb(),
    construct: () => absorb(),
  });
}

/** An object with the given fields that absorbs everything else. */
export function fake(fields) {
  return new Proxy(fields, {
    get: (target, key) => (key in target ? target[key] : absorb()),
    set: (target, key, value) => { target[key] = value; return true; },
  });
}

const WIDTH = 800;
const HEIGHT = 600;
const rect = () => ({ x: 0, y: 0, left: 0, top: 0, right: WIDTH, bottom: HEIGHT, width: WIDTH, height: HEIGHT });

/** Stands in for the DOM node behind a ref. */
export function fakeNode() {
  return fake({
    getBoundingClientRect: rect,
    clientWidth: WIDTH, clientHeight: HEIGHT, offsetWidth: WIDTH, offsetHeight: HEIGHT,
    width: WIDTH, height: HEIGHT, style: {}, value: "",
    getContext: () => absorb(),
    addEventListener: noop, removeEventListener: noop,
    focus: noop, blur: noop, contains: () => false,
  });
}

export function fakeEvent(type) {
  const node = fakeNode();
  return fake({
    type, target: node, currentTarget: node, key: "", button: 0,
    clientX: WIDTH / 2, clientY: HEIGHT / 2, pageX: WIDTH / 2, pageY: HEIGHT / 2,
    offsetX: WIDTH / 2, offsetY: HEIGHT / 2,
    preventDefault: noop, stopPropagation: noop, persist: noop,
  });
}

const queue = new Map();
let nextId = 1;

function schedule(fn, args, repeat) {
  if (typeof fn !== "function") return 0;
  const id = nextId++;
  queue.set(id, { fn, args, repeat });
  return id;
}

/** Runs every queued timer and animation frame once (intervals stay queued). */
export function tick() {
  for (const [id, task] of [...queue]) {
    if (!queue.has(id)) continue;
    if (!task.repeat) queue.delete(id);
    task.fn(...task.args);
  }
}

const g = globalThis;
g.window = g;
g.global = g;
g.self = g;
g.console = { log: noop, info: noop, warn: noop, error: noop, debug: noop };
g.setTimeout = (fn, ms, ...args) => schedule(fn, args, false);
g.setInterval = (fn, ms, ...args) => schedule(fn, args, true);
g.clearTimeout = g.clearInterval = (id) => queue.delete(id);
g.requestAnimationFrame = (fn) => schedule(fn, [Date.now()], false);
g.cancelAnimationFrame = (id) => queue.delete(id);
g.performance = { now: () => Date.now() };
g.innerWidth = 1024;
g.innerHeight = 768;
g.devicePixelRatio = 1;
g.addEventListener = noop;
g.removeEventListener = noop;
g.document = fake({
  body: fakeNode(), documentElement: fakeNode(),
  createElement: fakeNode, getElementById: fakeNode, querySelector: fakeNode,
  addEventListener: noop, removeEventListener: noop,
});
