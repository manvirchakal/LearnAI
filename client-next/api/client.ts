import axios, { AxiosError } from "axios";

/**
 * All requests go through the Next.js rewrite at /api-backend (see
 * next.config.mjs), so the browser only ever talks to one origin.
 */
export const API_BASE = "/api-backend";

export const apiClient = axios.create({ baseURL: API_BASE });

// No auth yet: identity is a plain header. Swap for a bearer token later.
const USER_ID = process.env.NEXT_PUBLIC_USER_ID || "default";
apiClient.interceptors.request.use((config) => {
  config.headers["X-User-Id"] = USER_ID;
  return config;
});

/** Human-readable message from an API error (FastAPI puts it in `detail`). */
export function errorMessage(err: unknown): string {
  if (err instanceof AxiosError) {
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === "string") return detail;
    return err.message;
  }
  return err instanceof Error ? err.message : String(err);
}

/** True for an HTTP error with the given status. */
export const isStatus = (err: unknown, status: number) =>
  err instanceof AxiosError && err.response?.status === status;

export default apiClient;
