import http from "node:http";
import https from "node:https";
import { Readable } from "node:stream";

/**
 * Same-origin proxy to the FastAPI backend: /api-backend/* → ${API_URL}/*.
 *
 * A route handler rather than a next.config rewrite, so API_URL is read at
 * runtime (one image works in every environment) and nothing times out or
 * buffers: request and response bodies, including SSE, are piped through and
 * generation calls on a slow local model can take as long as they need.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-connection",
  "transfer-encoding",
  "te",
  "trailer",
  "upgrade",
  "host",
]);

function backendUrl(path: string[], search: string): URL {
  const base = (process.env.API_URL || "http://localhost:8000").replace(/\/+$/, "");
  return new URL(`${base}/${path.map(encodeURIComponent).join("/")}${search}`);
}

function proxy(req: Request, { params }: { params: { path: string[] } }): Promise<Response> {
  const target = backendUrl(params.path, new URL(req.url).search);
  const headers: Record<string, string> = {};
  req.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key)) headers[key] = value;
  });

  return new Promise<Response>((resolve) => {
    const transport = target.protocol === "https:" ? https : http;
    const upstream = transport.request(target, { method: req.method, headers }, (res) => {
      const out = new Headers();
      for (const [key, value] of Object.entries(res.headers)) {
        if (value === undefined || HOP_BY_HOP.has(key)) continue;
        if (Array.isArray(value)) value.forEach((v) => out.append(key, v));
        else out.set(key, value);
      }
      const empty = req.method === "HEAD" || res.statusCode === 204 || res.statusCode === 304;
      const body = empty ? null : (Readable.toWeb(res) as ReadableStream<Uint8Array>);
      resolve(new Response(body, { status: res.statusCode ?? 502, headers: out }));
    });

    upstream.on("error", (err) =>
      resolve(Response.json({ detail: `Backend unreachable: ${err.message}` }, { status: 502 })),
    );
    req.signal?.addEventListener("abort", () => upstream.destroy());

    if (req.body) {
      Readable.fromWeb(req.body as Parameters<typeof Readable.fromWeb>[0]).pipe(upstream);
    } else {
      upstream.end();
    }
  });
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE, proxy as HEAD };
