// Bundles harness.js with React into bundle.js, which is committed: the server
// image has no Node. Keep react here at the version the client sandbox runs
// (client/package-lock.json); tests/test_game_check.py checks that.
import { buildSync } from "esbuild";

buildSync({
  entryPoints: ["harness.js"],
  outfile: "bundle.js",
  bundle: true,
  format: "iife",
  target: "es2020",
  // The development build, for full error messages to feed back to the model
  define: { "process.env.NODE_ENV": '"development"' },
  legalComments: "eof",
  logLevel: "warning",
});
console.log("built bundle.js");
