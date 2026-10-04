import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";
import type { GameResponse, StudyMaterials } from "@/types/study";

export const studyKey = (fileId: string, sectionId: string) => ["study", fileId, sectionId] as const;

const sectionPath = (fileId: string, sectionId: string) => `/books/${fileId}/sections/${sectionId}`;

/**
 * Study materials for a section. The backend returns its cache instantly and
 * only generates on a miss, so this is a query (POST is get-or-generate).
 */
export const useStudyMaterials = (fileId: string, sectionId: string) =>
  useQuery<StudyMaterials>({
    queryKey: studyKey(fileId, sectionId),
    queryFn: () =>
      apiClient.post(`${sectionPath(fileId, sectionId)}/study`, { force_regenerate: false }).then((r) => r.data),
    enabled: !!fileId && !!sectionId,
    staleTime: Infinity,
    retry: false, // generation is expensive; let the user retry explicitly
  });

export const useRegenerateStudy = (fileId: string, sectionId: string) => {
  const qc = useQueryClient();
  return useMutation<StudyMaterials, Error, void>({
    mutationFn: () =>
      apiClient.post(`${sectionPath(fileId, sectionId)}/study`, { force_regenerate: true }).then((r) => r.data),
    onSuccess: (data) => qc.setQueryData(studyKey(fileId, sectionId), data),
  });
};

export const useRegenerateGame = (fileId: string, sectionId: string) => {
  const qc = useQueryClient();
  return useMutation<GameResponse, Error, void>({
    mutationFn: () => apiClient.post(`${sectionPath(fileId, sectionId)}/game`).then((r) => r.data),
    onSuccess: ({ game_code }) =>
      qc.setQueryData<StudyMaterials>(studyKey(fileId, sectionId), (prev) => prev && { ...prev, game_code }),
  });
};
