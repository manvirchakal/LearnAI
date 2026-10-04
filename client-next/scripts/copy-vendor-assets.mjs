// Copies runtime assets that must be served as static files (no CDN at runtime).
import { cpSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const vendor = join(root, "public", "vendor");
mkdirSync(vendor, { recursive: true });

const assets = [
  // MathJax loads its components at runtime, so the whole es5 tree is served
  ["mathjax/es5", "mathjax"],
  // pdf.js worker for react-pdf; Next 14's minifier can't bundle pdfjs-dist 4's worker
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
