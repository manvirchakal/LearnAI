import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";
import type { ChatRequest, ChatResponse, ChatHistory } from "@/types/chat";

export const useChatHistory = (fileId: string, sectionName: string) =>
  useQuery<ChatHistory>({
    queryKey: ["chat-history", fileId, sectionName],
    queryFn: () =>
      apiClient.get("/chat-history", { params: { file_id: fileId, section_name: sectionName } }).then((r) => r.data),
    enabled: !!fileId && !!sectionName,
  });

export const useSendMessage = () => {
  const qc = useQueryClient();
  return useMutation<ChatResponse, Error, ChatRequest>({
    mutationFn: (payload) => apiClient.post("/api/chat", payload).then((r) => r.data),
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ["chat-history", variables.file_id, variables.section_name] });
    },
  });
};
