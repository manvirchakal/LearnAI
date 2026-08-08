// Single axios instance for every backend call. Session tokens live in
// HttpOnly cookies (see AuthContext) — never read or set here, never in
// localStorage — so `withCredentials: true` is what actually authenticates
// a request, not a header this file adds.
//
// REACT_APP_* because the client is still the Create React App build today;
// renaming to VITE_API_BASE_URL happens together with the CRA -> Vite
// migration, not before, so the two moves stay independently revertible.
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

// A 401 means the access token expired (or was never set) — try exactly
// once to refresh it via the refresh cookie before giving up. Any other
// failure, or a 401 on /auth/refresh itself, is passed through unchanged so
// callers don't loop.
let refreshInFlight = null;

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;
    if (!response || response.status !== 401 || config.__isRetry || config.url === '/auth/refresh') {
      return Promise.reject(error);
    }

    try {
      refreshInFlight = refreshInFlight || apiClient.post('/auth/refresh');
      await refreshInFlight;
    } catch (refreshError) {
      return Promise.reject(error);
    } finally {
      refreshInFlight = null;
    }

    return apiClient({ ...config, __isRetry: true });
  }
);

export default apiClient;
export { API_BASE_URL };
