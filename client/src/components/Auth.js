import React, { useEffect } from 'react';
import { useAuthenticator } from '@aws-amplify/ui-react';
import { useNavigate } from 'react-router-dom';

export function RequireAuth({ children }) {
  const { authStatus } = useAuthenticator((context) => [context.authStatus]);
  const navigate = useNavigate();

  useEffect(() => {
    if (authStatus !== 'authenticated') {
      navigate('/');
    }
  }, [authStatus, navigate]);

  return authStatus === 'authenticated' ? children : null;
}