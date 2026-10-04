"use client";
import { Alert, Box, Typography } from "@mui/material";
import { MathJax } from "better-react-mathjax";
import React, { ComponentType, useCallback, useEffect, useMemo, useRef, useState } from "react";
import ErrorBoundary from "@/components/shared/ErrorBoundary";
import Button from "@/components/ui/Button";

/**
 * Runs AI-generated game code. Contract (server/utils/code_utils.py):
 * the code is the BODY of a `Game()` function component, written with
 * React.createElement (no JSX) and ending in `return React.createElement(...)`.
 * These names are injected; nothing else is in scope.
 */
const SCOPE = ["React", "useState", "useEffect", "useRef", "useCallback", "useMemo", "MathJax"] as const;
const SCOPE_VALUES = [React, useState, useEffect, useRef, useCallback, useMemo, MathJax];

function compileGame(body: string): ComponentType {
  // eslint-disable-next-line no-new-func
  const factory = new Function(...SCOPE, `"use strict";\nreturn function Game() {\n${body}\n};`);
  const Game = factory(...SCOPE_VALUES);
  if (typeof Game !== "function") throw new Error("Game code did not produce a component");
  return Game as ComponentType;
}

interface Props {
  gameCode: string;
  onRetry?: () => void;
}

function GameError({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Alert severity="warning" action={onRetry && <Button size="small" onClick={onRetry}>New game</Button>}>
      <Typography variant="body2" gutterBottom>This game failed to run.</Typography>
      <Typography variant="caption" fontFamily="monospace">{message}</Typography>
    </Alert>
  );
}

export default function DynamicGameComponent({ gameCode, onRetry }: Props) {
  const compiled = useMemo(() => {
    try {
      return { Game: compileGame(gameCode), error: null };
    } catch (e) {
      return { Game: null, error: e instanceof Error ? e.message : String(e) };
    }
  }, [gameCode]);

  if (!compiled.Game) return <GameError message={compiled.error ?? "Unknown error"} onRetry={onRetry} />;
  const { Game } = compiled;

  return (
    <Box sx={{ width: "100%", minHeight: 400, bgcolor: "white", borderRadius: 1, border: "1px solid #e9ecef", overflow: "hidden" }}>
      <ErrorBoundary fallback={<GameError message="The game crashed while rendering." onRetry={onRetry} />}>
        <Game />
      </ErrorBoundary>
    </Box>
  );
}
