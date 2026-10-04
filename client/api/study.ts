import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient, { API_BASE, USER_ID, isStatus } from "./client";
import { readSSE } from "@/lib/sse";
import type { GameResponse, StudyMaterials, StudyStreamEvent } from "@/types/study";

/**
 * A study unit is anything with the study/game/chat endpoints under one path:
 * a book section or a collection.
 */
export type StudyUnit = string;

export const sectionUnit = (fileId: string, sectionId: string): StudyUnit =>
  `/books/${fileId}/sections/${encodeURIComponent(sectionId)}`;

export const collectionUnit = (collectionId: string): StudyUnit => `/collections/${collectionId}`;

export const studyKey = (unit: StudyUnit) => ["study", unit] as const;

/** Cached study materials, or null if this unit hasn't been generated yet. Never generates. */
export const useStudyMaterials = (unit: StudyUnit) =>
  useQuery<StudyMaterials | null>({
    queryKey: studyKey(unit),
    queryFn: () =>
      apiClient
        .get(`${unit}/study`)
        .then((r) => r.data)
        .catch((e) => {
          if (isStatus(e, 404)) return null;
          throw e;
        }),
    staleTime: Infinity,
  });

/** Generate (or fetch cached) study materials as a stream of SSE events. */
export async function* streamStudyMaterials(
  unit: StudyUnit,
  { force = false, signal }: { force?: boolean; signal?: AbortSignal } = {},
): AsyncGenerator<StudyStreamEvent> {
  const res = await fetch(`${API_BASE}${unit}/study/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-User-Id": USER_ID },
    body: JSON.stringify({ force_regenerate: force }),
    signal,
  });
  if (!res.ok) {
    const detail = await res.json().then((b) => b?.detail).catch(() => null);
    throw new Error(typeof detail === "string" ? detail : `Request failed (${res.status})`);
  }
  for await (const e of readSSE(res)) yield e as StudyStreamEvent;
}

export const useRegenerateGame = (unit: StudyUnit) => {
  const qc = useQueryClient();
  return useMutation<GameResponse, Error, void>({
    mutationFn: () => apiClient.post(`${unit}/game`).then((r) => r.data),
    onSuccess: ({ game_code }) =>
      qc.setQueryData<StudyMaterials | null>(studyKey(unit), (prev) => prev && { ...prev, game_code }),
  });
};
