import type { MathJax3Config } from "better-react-mathjax";

/** Served from public/vendor (copied from node_modules on install) — no CDN. */
export const MATHJAX_SRC = "/vendor/mathjax/tex-chtml.js";

export const mathJaxConfig: MathJax3Config = {
  loader: { load: ["input/tex", "output/chtml"] },
  tex: {
    inlineMath: [["$", "$"], ["\\(", "\\)"]],
    displayMath: [["$$", "$$"], ["\\[", "\\]"]],
  },
};
