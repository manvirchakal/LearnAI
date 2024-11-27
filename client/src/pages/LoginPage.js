import React from 'react';
import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import './LoginPage.css';
import logo from '../static/logo.png';

const LoginPage = () => {
  return (
    <div className="login-page-container">
      <img src={logo} alt="LearnAI Logo" className="login-logo" />
      <div className="login-form-container">
        <Authenticator>
          {({ signOut, user }) => (
            <main>
              <h1>Welcome {user?.username}</h1>
              <button onClick={signOut}>Sign out</button>
            </main>
          )}
        </Authenticator>
      </div>
    </div>
  );
};

export default LoginPage;