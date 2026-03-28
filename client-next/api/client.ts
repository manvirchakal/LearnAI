import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

// Inject user ID header on every request (no auth token — just identity)
apiClient.interceptors.request.use((config) => {
  // In a real app with auth this would inject a Bearer token.
  // For now, userId can be set via the Zustand store below.
  const userId = typeof window !== "undefined"
    ? (window as unknown as Record<string, string>).__learnai_user_id || "default"
    : "default";
  config.headers["x-user-id"] = userId;
  return config;
});

export default apiClient;
