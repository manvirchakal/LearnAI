import React, { useState, useEffect, useRef, useCallback } from 'react';
import { MathJaxContext, MathJax } from 'better-react-mathjax';
import ErrorBoundary from './ErrorBoundary';

const DynamicGameComponent = ({ gameCode }) => {
  const [error, setError] = useState(null);
  const [GameComponent, setGameComponent] = useState(null);
  const gameRef = useRef(null);
  const containerRef = useRef(null);

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
            <div ref={gameRef} style={{ width: '100%', height: '100%' }}>
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

  useEffect(() => {
    const resizeGame = () => {
      if (containerRef.current && gameRef.current) {
        const containerWidth = containerRef.current.clientWidth;
        const containerHeight = containerRef.current.clientHeight;
        const gameElement = gameRef.current.firstChild;
        if (gameElement) {
          const scale = Math.min(
            containerWidth / gameElement.offsetWidth,
            containerHeight / gameElement.offsetHeight
          );
          gameElement.style.transform = `scale(${scale})`;
          gameElement.style.transformOrigin = 'top left';
        }
      }
    };

    resizeGame();
    window.addEventListener('resize', resizeGame);
    return () => window.removeEventListener('resize', resizeGame);
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
      <div ref={containerRef} style={{ width: '100%', height: '100%', overflow: 'hidden' }}>
        <GameComponent />
      </div>
    </MathJaxContext>
  );
};

export default DynamicGameComponent;