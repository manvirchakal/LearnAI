import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";
import type { ChatHistory, ChatRequest, ChatResponse } from "@/types/chat";

export const chatKey = (fileId: string, sectionId: string) => ["chat", fileId, sectionId] as const;

const chatPath = (fileId: string, sectionId: string) => `/books/${fileId}/sections/${sectionId}/chat`;

export const useChatHistory = (fileId: string, sectionId: string) =>
  useQuery<ChatHistory>({
    queryKey: chatKey(fileId, sectionId),
    queryFn: () => apiClient.get(chatPath(fileId, sectionId)).then((r) => r.data),
    enabled: !!fileId && !!sectionId,
  });

export const useSendMessage = (fileId: string, sectionId: string) => {
  const qc = useQueryClient();
  return useMutation<ChatResponse, Error, ChatRequest>({
    mutationFn: (payload) => apiClient.post(chatPath(fileId, sectionId), payload).then((r) => r.data),
    onSuccess: ({ history }) => qc.setQueryData<ChatHistory>(chatKey(fileId, sectionId), { history }),
  });
};
