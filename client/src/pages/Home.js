import React, { useEffect } from 'react';
import { useAuthenticator, View } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import './Home.css';
import logo from '../static/logo.png';
import NavBar from './NavBar';
import { useNavigate } from 'react-router-dom';
import { Auth } from 'aws-amplify';

const Home = () => {
  const navigate = useNavigate();
  const { authStatus, user, signOut } = useAuthenticator((context) => [context.authStatus, context.user]);

  useEffect(() => {
    const setAuthToken = async () => {
      try {
        const session = await Auth.currentSession();
        const token = session.getIdToken().getJwtToken();
        localStorage.setItem('authToken', token);
      } catch (error) {
        console.error('Error setting auth token:', error);
      }
    };

    if (authStatus === 'authenticated') {
      setAuthToken();
    }
  }, [authStatus]);

  const handleSignOut = async () => {
    try {
      await Auth.signOut({ global: true });
      localStorage.clear();
      sessionStorage.clear();
      window.location.href = '/';
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  return (
    <View className="home-page">
      <NavBar />
      <div className="home-content">
        <div className="welcome-section">
          <img src={logo} alt="LearnAI Logo" className="home-logo" />
          <h1>Welcome back, {user?.username || 'User'}!</h1>
          <p className="subtitle">Ready to continue your learning journey?</p>
        </div>

        <div className="quick-actions">
          <div className="action-card" onClick={() => navigate('/questionnaire')}>
            <div className="card-content">
              <h3>Learning Style Quiz</h3>
              <p>Take our quiz to personalize your learning experience</p>
            </div>
          </div>

          <div className="action-card" onClick={() => navigate('/upload')}>
            <div className="card-content">
              <h3>Upload Textbook</h3>
              <p>Add new study materials to your library</p>
            </div>
          </div>

          <div className="action-card" onClick={() => navigate('/select-textbook')}>
            <div className="card-content">
              <h3>My Library</h3>
              <p>Access your uploaded textbooks and materials</p>
            </div>
          </div>
        </div>
      </div>
    </View>
  );
};

export default Home;
