// Replaces Amplify's Authenticator/useAuthenticator. Session state lives
// entirely server-side (HttpOnly cookies); this context just mirrors
// GET /auth/me into React state and exposes login/logout, matching the plan
// (see LearnAI's Phase 1 write-up: "Nothing in localStorage" — fixes the old
// Home.js:19, which read the Cognito token straight out of localStorage).
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import apiClient from '../api/client';

const AuthContext = createContext(undefined);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const { data } = await apiClient.get('/auth/me');
      setUser(data);
    } catch (error) {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    refreshUser().finally(() => setLoading(false));
  }, [refreshUser]);

  const loginWithGoogle = useCallback(async (idToken) => {
    const { data } = await apiClient.post('/auth/google', { id_token: idToken });
    setUser(data);
    return data;
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiClient.post('/auth/logout');
    } finally {
      setUser(null);
    }
  }, []);

  const value = { user, loading, isAuthenticated: user !== null, loginWithGoogle, logout, refreshUser };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
