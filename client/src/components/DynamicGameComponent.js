import React, { useState, useEffect, useRef, useCallback } from 'react';
import { MathJaxContext, MathJax } from 'better-react-mathjax';
import ErrorBoundary from './ErrorBoundary';

const DynamicGameComponent = ({ gameCode }) => {
  const [error, setError] = useState(null);
  const [GameComponent, setGameComponent] = useState(null);
  const gameRef = useRef(null);

  useEffect(() => {
    console.log("DynamicGameComponent received gameCode:", gameCode);
    setError(null);
    if (!gameCode || gameCode.startsWith("Error generating game code:")) {
      setError(gameCode || "No game code provided");
      return;
    }
    try {
      const ComponentFunction = new Function('React', 'useState', 'useEffect', 'useRef', 'useCallback', 'MathJax', `
        return function Game() {
          ${gameCode}
        }
      `);

      const CreatedComponent = () => {
        const GameFunction = ComponentFunction(React, React.useState, React.useEffect, React.useRef, React.useCallback, MathJax);
        return (
          <ErrorBoundary>
            <div ref={gameRef}>
              <GameFunction />
            </div>
          </ErrorBoundary>
        );
      };
      setGameComponent(() => CreatedComponent);
    } catch (err) {
      console.error('Error creating game component:', err);
      setError(`Error: ${err.message}\n\nStack: ${err.stack}\n\nGame Code:\n${gameCode}`);
    }
  }, [gameCode]);

  useEffect(() => {
    if (gameRef.current && window.MathJax) {
      window.MathJax.typesetPromise([gameRef.current]).catch((err) => {
        console.error('MathJax typesetting failed:', err);
      });
    }
  }, [GameComponent]);

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