import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";
import type { LearningProfile, ProfileAnswers, Questionnaire } from "@/types/profile";

export const useQuestionnaire = () =>
  useQuery<Questionnaire>({
    queryKey: ["profile", "questionnaire"],
    queryFn: () => apiClient.get("/profile/questionnaire").then((r) => r.data),
    staleTime: Infinity,
  });

/** Resolves to null when the user hasn't taken the questionnaire yet. */
export const useProfile = () =>
  useQuery<LearningProfile | null>({
    queryKey: ["profile"],
    queryFn: () =>
      apiClient
        .get("/profile")
        .then((r) => r.data)
        .catch((e) => {
          if (e?.response?.status === 404) return null;
          throw e;
        }),
  });

export const useSaveProfile = () => {
  const qc = useQueryClient();
  return useMutation<LearningProfile, Error, ProfileAnswers>({
    mutationFn: (answers) => apiClient.put("/profile", { answers }).then((r) => r.data),
    onSuccess: (profile) => qc.setQueryData(["profile"], profile),
  });
};
