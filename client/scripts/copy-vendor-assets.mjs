// Copies runtime assets that must be served as static files (no CDN at runtime).
import { cpSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { buildSync } from "esbuild";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const vendor = join(root, "public", "vendor");
mkdirSync(vendor, { recursive: true });

const assets = [
  // MathJax loads its components at runtime, so the whole es5 tree is served
  ["mathjax/es5", "mathjax"],
  // pdf.js worker for react-pdf, loaded by URL rather than bundled
  ["pdfjs-dist/build/pdf.worker.min.mjs", "pdf.worker.min.mjs"],
];

for (const [from, to] of assets) {
  const src = join(root, "node_modules", from);
  if (!existsSync(src)) {
    console.warn(`skipped ${from} (not installed)`);
    continue;
  }
  cpSync(src, join(vendor, to), { recursive: true });
  console.log(`copied ${from} → public/vendor/${to}`);
}

// React for the sandboxed game frame (public/sandbox/game.html). React 19 ships
// no UMD builds, so bundle the app's own React into window.React / window.ReactDOM.
buildSync({
  entryPoints: [join(root, "scripts", "sandbox-react.js")],
  outfile: join(vendor, "react", "react-bundle.js"),
  bundle: true,
  minify: true,
  format: "iife",
  target: "es2018",
  define: { "process.env.NODE_ENV": '"production"' },
  logLevel: "warning",
});
console.log("bundled react + react-dom/client → public/vendor/react/react-bundle.js");
