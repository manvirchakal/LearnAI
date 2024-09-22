import React from 'react';
import { Authenticator, useAuthenticator, View } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import './Login.css';
import logo from '../static/logo.png';
import NavBar from './NavBar';
import { useNavigate } from 'react-router-dom';

const Home = () => {
  const navigate = useNavigate();
  const { authStatus, user, signOut } = useAuthenticator((context) => [context.authStatus, context.user]);

  return (
    <View className="auth-wrapper">
      <NavBar />
      <div className="login-container">
        <img src={logo} alt="LearnAI Logo" className="logo" />
      </div>
      
      {authStatus === 'authenticated' && user ? (
        <div className="welcome-box">
          <h2>Welcome, {user.username || 'User'}!</h2>
          <button onClick={() => navigate('/questionnaire')}>Go to Questionnaire</button>
          <button onClick={signOut}>Sign out</button>
        </div>
      ) : authStatus === 'configuring' ? (
        <div>Loading...</div>
      ) : (
        <div className="login-box">
          <Authenticator>
            {({ signOut, user }) => (
              <main>
                <h1>Hello {user?.username || 'User'}</h1>
                <button onClick={signOut}>Sign out</button>
              </main>
            )}
          </Authenticator>
        </div>
      )}
    </View>
  );
};

export default Home;