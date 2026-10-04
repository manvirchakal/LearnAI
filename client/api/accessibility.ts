import { useMutation } from "@tanstack/react-query";
import apiClient from "./client";

export const useTranslate = () =>
  useMutation<{ translated_text: string }, Error, { text: string; target_language: string }>({
    mutationFn: (payload) => apiClient.post("/accessibility/translate", payload).then((r) => r.data),
  });

export const useSynthesizeSpeech = () =>
  useMutation<Blob, Error, { text: string; language?: string }>({
    mutationFn: ({ text, language = "en-US" }) =>
      apiClient.post("/accessibility/speech", { text, language }, { responseType: "blob" }).then((r) => r.data),
  });
