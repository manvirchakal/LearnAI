"use client";
import { Alert, Box, Typography } from "@mui/material";
import { useEffect, useRef, useState } from "react";
import Button from "@/components/ui/Button";

/**
 * Runs AI-generated game code in a sandboxed iframe (public/sandbox/game.html).
 *
 * Contract (server/utils/code_utils.py): the code is the BODY of a `Game()`
 * function component, written with React.createElement (no JSX) and ending in
 * `return React.createElement(...)`. React, the hooks and MathJax are in scope.
 *
 * The frame gets `sandbox="allow-scripts"` without `allow-same-origin`, so the
 * game runs in an opaque origin: it can't read the app's DOM, storage or
 * cookies, call the API, or navigate the page. The page's CSP also blocks
 * network requests. The code is sent with postMessage once the runtime is ready.
 */
export const SANDBOX_SRC = "/sandbox/game.html";

const MIN_HEIGHT = 420;
const MAX_HEIGHT = 900;

interface Props {
  gameCode: string;
  onRetry?: () => void;
}

type SandboxMessage =
  | { source: "learnai-game"; type: "ready" }
  | { source: "learnai-game"; type: "error"; message: string }
  | { source: "learnai-game"; type: "resize"; height: number };

function GameError({ message, onRetry, onReload }: { message: string; onRetry?: () => void; onReload: () => void }) {
  return (
    <Alert
      severity="warning"
      sx={{ mb: 1 }}
      action={
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button size="small" onClick={onReload}>Restart</Button>
          {onRetry && <Button size="small" onClick={onRetry}>New game</Button>}
        </Box>
      }
    >
      <Typography variant="body2" gutterBottom>This game hit an error.</Typography>
      <Typography variant="caption" fontFamily="monospace" sx={{ wordBreak: "break-word" }}>{message}</Typography>
    </Alert>
  );
}

export default function DynamicGameComponent({ gameCode, onRetry }: Props) {
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [run, setRun] = useState(0); // bumping it remounts the frame
  const [error, setError] = useState<string | null>(null);
  const [height, setHeight] = useState(MIN_HEIGHT);

  useEffect(() => {
    setError(null);
    const onMessage = (e: MessageEvent) => {
      // Only the frame we created; its origin is opaque ("null"), so match on the window
      if (e.source !== frameRef.current?.contentWindow) return;
      const msg = e.data as SandboxMessage;
      if (msg?.source !== "learnai-game") return;
      if (msg.type === "ready") {
        frameRef.current?.contentWindow?.postMessage({ type: "run", code: gameCode }, "*");
      } else if (msg.type === "error") {
        setError((prev) => prev ?? String(msg.message).slice(0, 500));
      } else if (msg.type === "resize" && Number.isFinite(msg.height)) {
        setHeight(Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, Math.ceil(msg.height))));
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [gameCode, run]);

  return (
    <Box>
      {error && <GameError message={error} onRetry={onRetry} onReload={() => setRun((n) => n + 1)} />}
      <Box sx={{ width: "100%", bgcolor: "white", borderRadius: 1, border: "1px solid #e9ecef", overflow: "hidden" }}>
        <iframe
          key={run}
          ref={frameRef}
          src={SANDBOX_SRC}
          title="Learning game"
          sandbox="allow-scripts"
          referrerPolicy="no-referrer"
          style={{ display: "block", width: "100%", height, border: 0 }}
        />
      </Box>
    </Box>
  );
}
