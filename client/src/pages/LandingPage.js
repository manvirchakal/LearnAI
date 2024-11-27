import React from 'react';
import { useNavigate } from 'react-router-dom';
import './LandingPage.css';
import logo from '../static/logo.png';

const LandingPage = () => {
  const navigate = useNavigate();

  return (
    <div className="landing-container">
      <div className="landing-content">
        <img src={logo} alt="LearnAI Logo" className="landing-logo" />
        <h1>Welcome to LearnAI</h1>
        <p className="landing-description">
          An innovative AI-driven educational platform designed to transform your learning experience. 
          Our platform personalizes education by tailoring content to your unique learning style, 
          ensuring you get the most out of your study materials.
        </p>
        <div className="feature-grid">
          <div className="feature-item">
            <h3>Personalized Learning</h3>
            <p>Content adapted to your learning style</p>
          </div>
          <div className="feature-item">
            <h3>AI Assistance</h3>
            <p>Real-time help and explanations</p>
          </div>
          <div className="feature-item">
            <h3>Interactive Learning</h3>
            <p>Engage with dynamic content</p>
          </div>
          <div className="feature-item">
            <h3>Accessibility</h3>
            <p>Learning materials for everyone</p>
          </div>
        </div>
        <button className="get-started-btn" onClick={() => navigate('/login')}>
          Get Started
        </button>
      </div>
    </div>
  );
};

export default LandingPage;