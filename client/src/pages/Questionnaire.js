// src/pages/Questionnaire.js
import React, { useState } from 'react';
import { Auth } from 'aws-amplify';
import { useNavigate } from 'react-router-dom';
import axios from 'axios'; // Add this import
import './Questionnaire.css'; // Import your styles
import { calculateLearningProfile } from '../utils/learningProfile';

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

const Questionnaire = () => {
  const [answers, setAnswers] = useState({});
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    try {
      const user = await Auth.currentAuthenticatedUser();
      
      console.log('Sending questionnaire answers:', answers);

      // Save questionnaire answers to your backend
      const response = await axios.post('http://localhost:8000/save-learning-profile', {
        answers: answers
      }, {
        headers: {
          'Authorization': `Bearer ${(await Auth.currentSession()).getIdToken().getJwtToken()}`
        }
      });

      console.log('Backend response:', response);

      if (response.status === 200) {
        console.log('Learning profile saved successfully');
        navigate('/study');
      } else {
        console.error('Error saving learning profile:', response);
      }
    } catch (error) {
      console.error('Error saving learning profile:', error);
      if (error.response) {
        console.error('Error data:', error.response.data);
        console.error('Error status:', error.response.status);
        console.error('Error headers:', error.response.headers);
      } else if (error.request) {
        console.error('Error request:', error.request);
      } else {
        console.error('Error message:', error.message);
      }
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
        <button type="submit">Submit</button>
      </form>
    </div>
  );
};

export default Questionnaire;
