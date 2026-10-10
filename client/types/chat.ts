export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatHistory {
  history: ChatMessage[];
}
