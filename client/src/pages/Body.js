// src/pages/Body.js
import React from 'react';
import './Body.css'; // Add styles for Body.js if needed

const Body = () => {
  return (
    <div className="main-content">
      <div className="content-container">
        {/* Left Blue Box (Welcome to LearnAI) */}
        <div className="welcome-box">
          <h1 className="title">Welcome to</h1>
          <h1 className="title">LearnAI</h1>
        </div>

        {/* Right White Box (What we do?) */}
        <div className="info-box">
          <div className="info-header">
            <span className="info-header-text">What we do?</span>
          </div>
          <ul className="info-list">
            <li>Personalize education by tailoring content to students' learning styles, emotional states, and performance.</li>
            <li>Promote educational equity and inclusivity, ensuring high-quality education is accessible to all learners.</li>
            <li>Allows users to upload textbooks/notes, provides real-time AI assistance, multilingual translation, and emotion-aware content.</li>
            <li>Built with AWS services, AI models (Anthropic's Claude Haiku), and tools like OpenCV for emotion detection and Amazon Polly for text-to-speech.</li>
            <li>Impact: Optimized for both high- and low-resource environments, aiming to close the digital divide and improve educational access globally.</li>
          </ul>
        </div>
      </div>

      {/* Footer */}
      <footer className="footer">
        <p>
          Interested? Fill out this <a href="#questionnaire" className="footer-link">questionnaire</a> so we can cater towards your learning style.
        </p>
      </footer>
    </div>
  );
};

export default Body;
