import { useMutation } from "@tanstack/react-query";
import apiClient from "./client";
import type { PresentationResult, TranscriptionResult } from "@/types/media";

export const useTranscribeYouTube = () =>
  useMutation<TranscriptionResult, Error, string>({
    mutationFn: (video_url) => apiClient.post("/media/youtube", { video_url }).then((r) => r.data),
  });

export const useTranscribeLecture = () =>
  useMutation<TranscriptionResult, Error, { audio: Blob; filename: string; title: string }>({
    mutationFn: ({ audio, filename, title }) => {
      const form = new FormData();
      form.append("audio", audio, filename);
      form.append("title", title);
      return apiClient.post("/media/lectures", form).then((r) => r.data);
    },
  });

export const useProcessPresentation = () =>
  useMutation<PresentationResult, Error, File>({
    mutationFn: (file) => {
      const form = new FormData();
      form.append("presentation", file);
      return apiClient.post("/media/presentations", form).then((r) => r.data);
    },
  });
