import React, { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './LoginPage.css';
import logo from '../static/logo.png';

const LoginPage = () => {
  const navigate = useNavigate();
  const { loginWithGoogle } = useAuth();
  const [error, setError] = useState(null);

  const handleSuccess = async (credentialResponse) => {
    setError(null);
    try {
      await loginWithGoogle(credentialResponse.credential);
      navigate('/home');
    } catch (err) {
      console.error('Google sign-in failed:', err);
      setError('Sign-in failed. Please try again.');
    }
  };

  return (
    <div className="login-page-container">
      <img src={logo} alt="LearnAI Logo" className="login-logo" />
      <div className="login-form-container">
        <GoogleLogin
          onSuccess={handleSuccess}
          onError={() => setError('Sign-in failed. Please try again.')}
        />
        {error && <p className="auth-error">{error}</p>}
      </div>
    </div>
  );
};

export default LoginPage;
