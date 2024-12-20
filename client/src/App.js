import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import { Authenticator } from '@aws-amplify/ui-react';
import { Amplify } from 'aws-amplify';
import Home from './pages/Home';
import Study from './pages/Study';
import Questionnaire from './pages/Questionnaire';
import Upload from './pages/Upload';
import SelectTextbook from './pages/SelectTextbook';
import { RequireAuth } from './components/Auth';
import './latex-styles.css';
import { MathJaxContext } from 'better-react-mathjax';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';

Amplify.configure({
    Auth: {
        region: process.env.REACT_APP_AWS_REGION,
        userPoolId: process.env.REACT_APP_USER_POOL_ID,
        userPoolWebClientId: process.env.REACT_APP_USER_POOL_WEB_CLIENT_ID,
    }
});

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
      <Authenticator.Provider>
        <Router>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/home" element={<RequireAuth><Home /></RequireAuth>} />
            <Route path="/study" element={<RequireAuth><Study /></RequireAuth>} />
            <Route path="/questionnaire" element={<RequireAuth><Questionnaire /></RequireAuth>} />
            <Route path="/upload" element={<RequireAuth><Upload /></RequireAuth>} />
            <Route path="/select-textbook" element={<RequireAuth><SelectTextbook /></RequireAuth>} />
          </Routes>
        </Router>
      </Authenticator.Provider>
    </MathJaxContext>
  );
}

export default App;
