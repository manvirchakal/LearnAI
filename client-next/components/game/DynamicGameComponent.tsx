"use client";
import { useEffect, useRef, useState } from "react";
import { Box, Typography, Alert } from "@mui/material";

interface Props {
  gameCode: string;
  onError?: (err: string) => void;
}

/**
 * Executes AI-generated React game code at runtime using new Function().
 * The generated code is expected to export a default React component as a
 * self-contained string, e.g.:
 *   function Game() { ... return <div>...</div>; }
 *   return Game;
 *
 * We inject React, useState, useEffect, useRef into the sandbox scope so the
 * generated code can use hooks without explicit imports.
 */
export default function DynamicGameComponent({ gameCode, onError }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!gameCode || !containerRef.current) return;
    setError(null);

    try {
      // Dynamically import React DOM to avoid SSR issues
      import("react-dom/client").then((ReactDOM) => {
        try {
          const React = require("react");
          const { useState, useEffect, useRef, useCallback, useMemo } = React;

          // Build sandbox — inject common hooks so generated code can use them
          // eslint-disable-next-line no-new-func
          const factory = new Function(
            "React",
            "useState",
            "useEffect",
            "useRef",
            "useCallback",
            "useMemo",
            `"use strict"; ${gameCode}`
          );

          const GameComponent = factory(
            React, useState, useEffect, useRef, useCallback, useMemo
          );

          if (typeof GameComponent !== "function") {
            throw new Error("Generated code did not return a React component.");
          }

          const root = ReactDOM.createRoot(containerRef.current!);
          root.render(React.createElement(GameComponent));

          // Cleanup on unmount
          return () => {
            try { root.unmount(); } catch (_) {}
          };
        } catch (e: any) {
          const msg = e?.message || String(e);
          setError(msg);
          onError?.(msg);
        }
      });
    } catch (e: any) {
      const msg = e?.message || String(e);
      setError(msg);
      onError?.(msg);
    }
  }, [gameCode]);

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        <Typography variant="body2" fontFamily="monospace" fontSize={12}>
          Game render error: {error}
        </Typography>
      </Alert>
    );
  }

  return (
    <Box
      ref={containerRef}
      sx={{
        width: "100%",
        minHeight: 400,
        bgcolor: "white",
        borderRadius: 1,
        overflow: "hidden",
        "& *": { boxSizing: "border-box" },
      }}
    />
  );
}
