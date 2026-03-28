export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  message: string;
  user_id: string;
  file_id: string;
  section_name: string;
  collection_id?: string;
  language?: string;
}

export interface ChatResponse {
  reply: string;
  history?: ChatMessage[];
}

export interface ChatHistory {
  history: ChatMessage[];
}
