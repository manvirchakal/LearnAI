import { useMutation } from "@tanstack/react-query";
import apiClient from "./client";
import type { TranscriptionResult, PresentationResult } from "@/types/media";

export const useTranscribeYouTube = () =>
  useMutation<TranscriptionResult, Error, string>({
    mutationFn: (video_url) =>
      apiClient.post("/transcribe-youtube", { video_url }).then((r) => r.data),
  });

export const useTranscribeLecture = () =>
  useMutation<TranscriptionResult, Error, FormData>({
    mutationFn: (formData) =>
      apiClient
        .post("/transcribe-lecture", formData, { headers: { "Content-Type": "multipart/form-data" } })
        .then((r) => r.data),
  });

export const useProcessPresentation = () =>
  useMutation<PresentationResult, Error, FormData>({
    mutationFn: (formData) =>
      apiClient
        .post("/process-presentation", formData, { headers: { "Content-Type": "multipart/form-data" } })
        .then((r) => r.data),
  });
