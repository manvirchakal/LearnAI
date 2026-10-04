import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";
import type { StudyUnit } from "./study";
import type { ChatHistory, ChatRequest, ChatResponse } from "@/types/chat";

export const chatKey = (unit: StudyUnit) => ["chat", unit] as const;

export const useChatHistory = (unit: StudyUnit) =>
  useQuery<ChatHistory>({
    queryKey: chatKey(unit),
    queryFn: () => apiClient.get(`${unit}/chat`).then((r) => r.data),
  });

export const useSendMessage = (unit: StudyUnit) => {
  const qc = useQueryClient();
  return useMutation<ChatResponse, Error, ChatRequest>({
    mutationFn: (payload) => apiClient.post(`${unit}/chat`, payload).then((r) => r.data),
    onSuccess: ({ history }) => qc.setQueryData<ChatHistory>(chatKey(unit), { history }),
  });
};
