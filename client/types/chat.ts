export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  message: string;
  language?: string;
}

export interface ChatHistory {
  history: ChatMessage[];
}

export interface ChatResponse extends ChatHistory {
  reply: string;
}
