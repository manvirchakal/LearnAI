const GAME_CSP = [
  "sandbox allow-scripts",
  "default-src 'none'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
  "style-src 'unsafe-inline'",
  "img-src data: blob:",
  "font-src data:",
  "media-src data: blob:",
  "connect-src 'none'",
  "form-action 'none'",
  "base-uri 'none'",
].join("; ");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Self-contained server bundle for the Docker image (.next/standalone)
  output: "standalone",
  async headers() {
    return [
      {
        // The game frame: even if opened directly, it stays sandboxed (opaque
        // origin) and can't make network requests. 'unsafe-eval' is how the
        // generated code is compiled; 'self' serves React and MathJax.
        source: "/sandbox/:path*",
        headers: [
          { key: "Content-Security-Policy", value: GAME_CSP },
          { key: "Referrer-Policy", value: "no-referrer" },
          { key: "Access-Control-Allow-Origin", value: "*" },
        ],
      },
      {
        // The game frame's origin is opaque, so its scripts are cross-origin
        // loads; CORS lets it see their error messages (see sandbox/game.html)
        source: "/vendor/:path*",
        headers: [{ key: "Access-Control-Allow-Origin", value: "*" }],
      },
    ];
  },
  // /api-backend/* is proxied to the FastAPI backend by app/api-backend/[...path]/route.ts
};

export default nextConfig;
