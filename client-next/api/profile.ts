import { useMutation, useQuery } from "@tanstack/react-query";
import apiClient from "./client";
import type { LearningProfile, SaveProfileResponse } from "@/types/profile";

export const useGetProfile = () =>
  useQuery<LearningProfile>({
    queryKey: ["profile"],
    queryFn: () => apiClient.get("/profile/learning-profile").then((r) => r.data),
    retry: false,
  });

export const useSaveProfile = () =>
  useMutation<SaveProfileResponse, Error, Record<string, unknown>>({
    mutationFn: (answers) =>
      apiClient.post("/profile/save-learning-profile", { answers }).then((r) => r.data),
  });
