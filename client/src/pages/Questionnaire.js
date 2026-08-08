// src/pages/Questionnaire.js
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import './Questionnaire.css'; // Import your styles
import { calculateLearningProfile } from '../utils/learningProfile';
import NavBar from './NavBar';

const learningCategories = {
  Visual: [
    "I find it easier to understand new information when it is presented in diagrams, charts, or graphs.",
    "I prefer learning new concepts by observing demonstrations.",
    "I often visualize concepts or problems in my mind to help me solve them.",
    "I use colors, symbols, or drawings when taking notes to help me organize my thoughts.",
    "I remember information better when I see it written down or displayed on a screen",
  ],
  Auditory: [
    "I learn better when I listen to explanations rather than read them.",
    "I prefer to learn by listening to audio lectures or podcasts.",
    "I remember information better when I hear it spoken aloud.",
    "I use mnemonics or chants to help me memorize information.",
    "I learn best by discussing concepts with others.",
  ],
  ReadingWriting: [
    "I understand new ideas best when I write them down.",
    "I learn best by reading textbooks or articles.",
    "I use flashcards or mind maps to help me memorize information.",
    "I prefer to learn by reading and writing rather than listening or watching.",
    "I use diagrams or charts to help me understand and remember information.",
  ],
  Kinesthetic: [
    "I enjoy working with physical models or doing hands-on activities to learn.",
    "I learn best by doing experiments or practical activities.",
    "I use role-playing or simulations to help me understand and apply new concepts.",
    "I prefer to learn by solving real-world problems or puzzles.",
    "I use physical models or manipulatives to help me visualize and understand information.",
  ]
};

const options = [
  "Strongly Disagree",
  "Somewhat Disagree",
  "Neutral",
  "Somewhat Agree",
  "Strongly Agree"
];

// Answers arrive from the form as { [category]: { [questionIndex]: "1".."5" } }.
// The API wants { [category]: [1, 2, ...] } — numeric-string object keys are
// always iterated in ascending order in JS, so Object.values already comes
// back in question order.
function toAnswerLists(answers) {
  const result = {};
  for (const category of Object.keys(learningCategories)) {
    result[category] = Object.values(answers[category] || {}).map(Number);
  }
  return result;
}

function isComplete(answers) {
  return Object.entries(learningCategories).every(
    ([category, questions]) => Object.keys(answers[category] || {}).length === questions.length
  );
}

// A placeholder until Phase 2 replaces this with an LLM-generated
// description over the same submission shape — see routers/profile.py.
function describeProfile(scores) {
  const ranked = Object.entries(scores).sort(([, a], [, b]) => b - a);
  const [topCategory] = ranked[0];
  const label = topCategory.replace(/([A-Z])/g, ' $1').trim();
  return `Shows the strongest preference for ${label} learning, based on the questionnaire responses.`;
}

const Questionnaire = () => {
  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);

    if (!isComplete(answers)) {
      setError('Please answer every question before submitting.');
      return;
    }

    setSubmitting(true);
    try {
      const answerLists = toAnswerLists(answers);
      const scores = calculateLearningProfile(answers);
      const description = describeProfile(scores);

      await apiClient.put('/api/v1/profile', {
        answers: answerLists,
        scores,
        description,
        questionnaire_version: 1,
      });

      navigate('/study');
    } catch (err) {
      console.error('Error saving learning profile:', err);
      setError('Something went wrong saving your profile. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAnswerChange = (category, questionIndex, value) => {
    setAnswers(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [questionIndex]: value
      }
    }));
  };

  return (
      <>
      <NavBar />
      <div className="questionnaire-container">
        <h2>Fill out this questionnaire so we can cater LearnAI based on your learning style</h2>
      <form onSubmit={handleSubmit}>
        {Object.keys(learningCategories).map((category, categoryIndex) => (
          <div key={categoryIndex} className="category">
            <h3>{category} Learning Style</h3>
            {learningCategories[category].map((question, questionIndex) => (
              <div key={questionIndex} className="question">
                <p>{categoryIndex + 1}.{questionIndex + 1}. {question}</p>
                <div className="options">
                  {options.map((option, idx) => (
                    <label key={idx}>
                      <input
                        type="radio"
                        name={`question-${categoryIndex}-${questionIndex}`}
                        value={idx + 1}
                        onChange={(e) => handleAnswerChange(category, questionIndex, e.target.value)}
                      />
                      {option}
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ))}
        {error && <p className="questionnaire-error">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : 'Submit'}
        </button>
        </form>
      </div>
    </>
  );
};

export default Questionnaire;
