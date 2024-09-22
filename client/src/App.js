import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import { Authenticator } from '@aws-amplify/ui-react';
import { Amplify } from 'aws-amplify';
import Home from './pages/Home';
import Study from './pages/Study';
import Questionnaire from './pages/Questionnaire';
import Upload from './pages/Upload';
import { RequireAuth } from './components/Auth';
import './latex-styles.css';
import { MathJaxContext } from 'better-react-mathjax';

Amplify.configure({
    Auth: {
        region: 'us-east-1',
        userPoolId: 'us-east-1_48IJcanGU',
        userPoolWebClientId: '7ri0hp1t0jl1l2cb3vdnok67tu',
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
            <Route path="/" element={<Home />} />
            <Route path="/study" element={<RequireAuth><Study /></RequireAuth>} />
            <Route path="/questionnaire" element={<RequireAuth><Questionnaire /></RequireAuth>} />
            <Route path="/upload" element={<RequireAuth><Upload /></RequireAuth>} />
          </Routes>
        </Router>
      </Authenticator.Provider>
    </MathJaxContext>
  );
}

export default App;
