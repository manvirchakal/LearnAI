import { useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";
import type { NarrativeResult } from "@/types/study";
import { useStudyStore } from "@/store/studyStore";

interface GenerateNarrativeInput {
  collectionId: string;
  sectionName: string;
}

interface GenerateGameInput {
  collection_id: string;
  section_name: string;
}

interface GameCodeResult {
  game_code: string;
}

export const useGenerateNarrative = () => {
  const qc = useQueryClient();
  const { setNarrative } = useStudyStore();
  return useMutation<NarrativeResult, Error, GenerateNarrativeInput>({
    mutationFn: ({ collectionId, sectionName }) =>
      apiClient
        .post(`/generate-narrative/${collectionId}`, { section_name: sectionName })
        .then((r) => r.data),
    onSuccess: (data, variables) => {
      setNarrative(data);
      qc.setQueryData(["narrative", variables.collectionId, variables.sectionName], data);
    },
  });
};

export const useGenerateGameCode = () =>
  useMutation<GameCodeResult, Error, GenerateGameInput>({
    mutationFn: (payload) => apiClient.post("/generate-game-code", payload).then((r) => r.data),
  });
