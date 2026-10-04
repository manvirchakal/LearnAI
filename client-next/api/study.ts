import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient, { API_BASE, USER_ID, isStatus } from "./client";
import { readSSE } from "@/lib/sse";
import type { GameResponse, StudyMaterials, StudyStreamEvent } from "@/types/study";

export const studyKey = (fileId: string, sectionId: string) => ["study", fileId, sectionId] as const;

const sectionPath = (fileId: string, sectionId: string) => `/books/${fileId}/sections/${sectionId}`;

/** Cached study materials, or null if this section hasn't been generated yet. Never generates. */
export const useStudyMaterials = (fileId: string, sectionId: string) =>
  useQuery<StudyMaterials | null>({
    queryKey: studyKey(fileId, sectionId),
    queryFn: () =>
      apiClient
        .get(`${sectionPath(fileId, sectionId)}/study`)
        .then((r) => r.data)
        .catch((e) => {
          if (isStatus(e, 404)) return null;
          throw e;
        }),
    enabled: !!fileId && !!sectionId,
    staleTime: Infinity,
  });

/** Generate (or fetch cached) study materials as a stream of SSE events. */
export async function* streamStudyMaterials(
  fileId: string,
  sectionId: string,
  { force = false, signal }: { force?: boolean; signal?: AbortSignal } = {},
): AsyncGenerator<StudyStreamEvent> {
  const res = await fetch(`${API_BASE}${sectionPath(fileId, sectionId)}/study/stream`, {
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

export const useRegenerateGame = (fileId: string, sectionId: string) => {
  const qc = useQueryClient();
  return useMutation<GameResponse, Error, void>({
    mutationFn: () => apiClient.post(`${sectionPath(fileId, sectionId)}/game`).then((r) => r.data),
    onSuccess: ({ game_code }) =>
      qc.setQueryData<StudyMaterials | null>(studyKey(fileId, sectionId), (prev) => prev && { ...prev, game_code }),
  });
};
