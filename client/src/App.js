import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import Home from './pages/Home';
import Study from './pages/Study';
import Questionnaire from './pages/Questionnaire';
import Upload from './pages/Upload';
import Reader from './pages/Reader';
import SelectTextbook from './pages/SelectTextbook';
import Collections from './pages/Collections';
import { RequireAuth } from './components/Auth';
import { AuthProvider } from './context/AuthContext';
import './latex-styles.css';
import { MathJaxContext } from 'better-react-mathjax';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';

function App() {
  return (
    <MathJaxContext
      config={{
        tex: {
          inlineMath: [['\\(', '\\)']],
          displayMath: [['\\[', '\\]']],
        },
        options: {
          skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre'],
          processHtmlClass: 'math-inline|math-display'
        },
        startup: {
          typeset: false
        }
      }}
    >
      <GoogleOAuthProvider clientId={process.env.REACT_APP_GOOGLE_CLIENT_ID || ''}>
        <AuthProvider>
          <Router>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/home" element={<RequireAuth><Home /></RequireAuth>} />
              <Route path="/study" element={<RequireAuth><Study /></RequireAuth>} />
              <Route path="/questionnaire" element={<RequireAuth><Questionnaire /></RequireAuth>} />
              <Route path="/upload" element={<RequireAuth><Upload /></RequireAuth>} />
              <Route path="/materials/:materialId" element={<RequireAuth><Reader /></RequireAuth>} />
              <Route path="/select-textbook" element={<RequireAuth><SelectTextbook /></RequireAuth>} />
              <Route path="/collections" element={<RequireAuth><Collections /></RequireAuth>} />
            </Routes>
          </Router>
        </AuthProvider>
      </GoogleOAuthProvider>
    </MathJaxContext>
  );
}

export default App;
