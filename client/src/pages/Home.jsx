import React from 'react';
import './Home.css';
import logo from '../static/logo.png';
import NavBar from './NavBar';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Home = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  return (
    <div className="home-page">
      <NavBar />
      <div className="home-content">
        <div className="welcome-section">
          <img src={logo} alt="LearnAI Logo" className="home-logo" />
          <h1>Welcome back, {user?.name || 'User'}!</h1>
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
              <h3>Upload Material</h3>
              <p>Add new study materials to your library</p>
            </div>
          </div>

          <div className="action-card" onClick={() => navigate('/collections')}>
            <div className="card-content">
              <h3>My Collections</h3>
              <p>Browse and create your study collections</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;
