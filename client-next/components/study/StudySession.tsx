"use client";
import { useQueryClient } from "@tanstack/react-query";
import { createContext, ReactNode, useCallback, useContext, useEffect, useRef, useState } from "react";
import { errorMessage } from "@/api/client";
import { streamStudyMaterials, studyKey, useStudyMaterials } from "@/api/study";
import type { StudyMaterials, StudyStage } from "@/types/study";

export type StudyStatus = "loading" | "streaming" | "ready" | "error";

interface StudySession {
  fileId: string;
  sectionId: string;
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
 * One generation session per section, shared by the narrative, game and
 * diagram panels. Loads cached materials; on a miss, streams generation
 * (narrative tokens first) and writes the result into the query cache.
 */
export function StudySessionProvider({
  fileId,
  sectionId,
  children,
}: {
  fileId: string;
  sectionId: string;
  children: ReactNode;
}) {
  const qc = useQueryClient();
  const cached = useStudyMaterials(fileId, sectionId);
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
        for await (const e of streamStudyMaterials(fileId, sectionId, { force, signal: controller.signal })) {
          if (e.event === "token") setStreamingText((t) => t + e.data);
          else if (e.event === "stage") setActivity(NEXT_ACTIVITY[e.data] ?? null);
          else if (e.event === "error") throw new Error(e.data);
          else if (e.event === "done") {
            qc.setQueryData(studyKey(fileId, sectionId), e.data);
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
    [fileId, sectionId, qc],
  );

  // First visit to a section: nothing cached, so start generating
  useEffect(() => {
    if (cached.isSuccess && cached.data === null) generate(false);
    return () => abortRef.current?.abort();
  }, [cached.isSuccess, cached.data, generate]);

  const error = streamError ?? (cached.error ? errorMessage(cached.error) : null);
  const status: StudyStatus = streaming ? "streaming" : error ? "error" : cached.data ? "ready" : "loading";

  return (
    <Ctx.Provider
      value={{
        fileId,
        sectionId,
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
