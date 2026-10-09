import { useQuery } from "@tanstack/react-query";
import apiClient from "./client";
import type { StudyUnit } from "./study";
import type { ChatHistory } from "@/types/chat";

export const chatKey = (unit: StudyUnit) => ["chat", unit] as const;

/** Stored history. New turns stream through useChat (components/study/ChatPanel.tsx). */
export const useChatHistory = (unit: StudyUnit) =>
  useQuery<ChatHistory>({
    queryKey: chatKey(unit),
    queryFn: () => apiClient.get(`${unit}/chat`).then((r) => r.data),
  });
