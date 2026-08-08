import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function RequireAuth({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      navigate('/');
    }
  }, [loading, isAuthenticated, navigate]);

  if (loading) {
    return null;
  }

  return isAuthenticated ? children : null;
}
