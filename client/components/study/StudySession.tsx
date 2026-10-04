"use client";
import { Box, Typography } from "@mui/material";
import { useQueryClient } from "@tanstack/react-query";
import { createContext, ReactNode, useCallback, useContext, useEffect, useRef, useState } from "react";
import { errorMessage } from "@/api/client";
import { streamStudyMaterials, studyKey, useStudyMaterials, type StudyUnit } from "@/api/study";
import type { StudyMaterials, StudyStage } from "@/types/study";

/** idle: nothing generated yet and generation wasn't started automatically */
export type StudyStatus = "loading" | "idle" | "streaming" | "ready" | "error";

interface StudySession {
  unit: StudyUnit;
  status: StudyStatus;
  materials: StudyMaterials | null;
  /** Narrative text received so far while streaming */
  streamingText: string;
  /** What the agent is doing now, for progress labels */
  activity: string | null;
  error: string | null;
  generate: (force?: boolean) => void;
}

/** Label for the work that starts after `stage` finishes. */
const NEXT_ACTIVITY: Record<StudyStage, string | null> = {
  load_cached: "Finding related material…",
  rag: "Writing your personalized narrative…",
  narrative: "Designing a game…",
  game_idea: "Building the game…",
  game_code: "Testing the game…",
  validate_code: "Drawing diagrams…",
  diagrams: "Saving…",
  save: null,
};

const Ctx = createContext<StudySession | null>(null);

/**
 * One generation session per study unit (book section or collection), shared by the narrative, game and
 * diagram panels. Loads cached materials; on a miss, streams generation
 * (narrative tokens first) and writes the result into the query cache.
 */
export function StudySessionProvider({
  unit,
  autoGenerate = true,
  children,
}: {
  unit: StudyUnit;
  /** Start generating on a cache miss (sections); collections wait for the learner */
  autoGenerate?: boolean;
  children: ReactNode;
}) {
  const qc = useQueryClient();
  const cached = useStudyMaterials(unit);
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [activity, setActivity] = useState<string | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const generate = useCallback(
    async (force = false) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setStreaming(true);
      setStreamingText("");
      setActivity("Getting started…");
      setStreamError(null);
      try {
        let finished = false;
        for await (const e of streamStudyMaterials(unit, { force, signal: controller.signal })) {
          if (e.event === "token") setStreamingText((t) => t + e.data);
          else if (e.event === "stage") setActivity(NEXT_ACTIVITY[e.data] ?? null);
          else if (e.event === "error") throw new Error(e.data);
          else if (e.event === "done") {
            qc.setQueryData(studyKey(unit), e.data);
            finished = true;
          }
        }
        if (!finished) throw new Error("The connection closed before generation finished");
      } catch (err) {
        if (!controller.signal.aborted) setStreamError(errorMessage(err));
      } finally {
        if (abortRef.current === controller) {
          setStreaming(false);
          setActivity(null);
        }
      }
    },
    [unit, qc],
  );

  // First visit to a unit: nothing cached, so start generating
  useEffect(() => {
    if (autoGenerate && cached.isSuccess && cached.data === null) generate(false);
  }, [autoGenerate, cached.isSuccess, cached.data, generate]);
  useEffect(() => () => abortRef.current?.abort(), [unit]);

  const error = streamError ?? (cached.error ? errorMessage(cached.error) : null);
  const status: StudyStatus = streaming
    ? "streaming"
    : error
      ? "error"
      : cached.data
        ? "ready"
        : cached.isSuccess && !autoGenerate
          ? "idle"
          : "loading";

  return (
    <Ctx.Provider
      value={{
        unit,
        status,
        materials: cached.data ?? null,
        streamingText,
        activity,
        error,
        generate: (force) => void generate(force),
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useStudySession(): StudySession {
  const session = useContext(Ctx);
  if (!session) throw new Error("useStudySession must be used inside <StudySessionProvider>");
  return session;
}

/** Placeholder for the game and diagram panels before anything is generated. */
export function NotYet() {
  return (
    <Box sx={{ p: 4, textAlign: "center" }}>
      <Typography color="text.secondary" variant="body2">Generate the study guide first.</Typography>
    </Box>
  );
}
