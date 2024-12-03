import React, { useEffect, useState } from 'react';
import { Authenticator, useAuthenticator, View } from '@aws-amplify/ui-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Auth } from 'aws-amplify';
import '@aws-amplify/ui-react/styles.css';
import './LoginPage.css';
import logo from '../static/logo.png';

const LoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [showAuth, setShowAuth] = useState(false);
  
  // Check if coming from landing page
  const isNewUser = location.search.includes('signup=true');
  
  useEffect(() => {
    const cleanAuth = async () => {
      try {
        await Auth.signOut({ global: true });
        setTimeout(() => setShowAuth(true), 100);
      } catch (error) {
        console.error('Error clearing auth:', error);
        setShowAuth(true);
      }
    };
    
    cleanAuth();
    
    return () => setShowAuth(false);
  }, []);

  if (!showAuth) {
    return (
      <div className="login-page-container">
        <img src={logo} alt="LearnAI Logo" className="login-logo" />
        <div className="login-form-container">
          <div className="auth-success-message">
            <div className="loading-spinner"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page-container">
      <img src={logo} alt="LearnAI Logo" className="login-logo" />
      <div className="login-form-container">
        <Authenticator
          hideSignUp={!isNewUser} // Show sign-up only for new users
          initialState={isNewUser ? "signUp" : "signIn"} // Start with sign-up if new user
          components={{
            SignIn: {
              Footer() {
                return null;
              },
            },
          }}
        >
          {({ user }) => {
            navigate('/home');
            return null;
          }}
        </Authenticator>
      </div>
    </div>
  );
};

export default LoginPage;