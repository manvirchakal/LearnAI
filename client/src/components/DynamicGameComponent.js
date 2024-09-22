import React, { useState, useEffect } from 'react';
import { MathJaxContext, MathJax } from 'better-react-mathjax';
import ErrorBoundary from './ErrorBoundary';

const DynamicGameComponent = ({ gameCode }) => {
  const [error, setError] = useState(null);
  const [GameComponent, setGameComponent] = useState(null);

  useEffect(() => {
    setError(null);
    try {
      // Wrap the game code in a try-catch block
      const wrappedGameCode = `
        try {
          ${gameCode}
        } catch (error) {
          console.error('Error in game code:', error);
          return React.createElement('div', null, 
            React.createElement('h3', null, 'Error in game code:'),
            React.createElement('pre', null, error.toString())
          );
        }
      `;

      // Create a new function that returns a React component
      const ComponentFunction = new Function('React', 'useState', 'useEffect', 'MathJax', `
        return function Game() {
          ${wrappedGameCode}
          return elements;
        }
      `);

      // Create the component
      const CreatedComponent = () => {
        const Game = ComponentFunction(React, useState, useEffect, MathJax);
        return (
          <ErrorBoundary>
            <Game />
          </ErrorBoundary>
        );
      };
      setGameComponent(() => CreatedComponent);
    } catch (err) {
      console.error('Error creating game component:', err);
      setError(`Error: ${err.message}\n\nStack: ${err.stack}\n\nGame Code:\n${gameCode}`);
    }
  }, [gameCode]);

  if (error) {
    return (
      <div>
        <h3>Error loading game:</h3>
        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {error}
        </pre>
      </div>
    );
  }

  if (!GameComponent) {
    return <div>Loading game...</div>;
  }

  return (
    <MathJaxContext>
      <GameComponent />
    </MathJaxContext>
  );
};

export default DynamicGameComponent;