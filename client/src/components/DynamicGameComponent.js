import React, { useState, useEffect } from 'react';
import { MathJaxContext, MathJax } from 'better-react-mathjax';

const DynamicGameComponent = ({ gameCode }) => {
  const [error, setError] = useState(null);
  const [GameComponent, setGameComponent] = useState(null);

  useEffect(() => {
    setError(null);
    try {
      // Create a new function that returns a React component
      const ComponentFunction = new Function('React', 'useState', 'useEffect', 'MathJax', `
        return function Game() {
          ${gameCode}
          return React.createElement(React.Fragment, null, elements);
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

// Add this ErrorBoundary component
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ error, errorInfo });
    console.error("Uncaught error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div>
          <h3>Something went wrong in the game component.</h3>
          <details style={{ whiteSpace: 'pre-wrap' }}>
            {this.state.error && this.state.error.toString()}
            <br />
            {this.state.errorInfo && this.state.errorInfo.componentStack}
          </details>
        </div>
      );
    }

    return this.props.children;
  }
}

export default DynamicGameComponent;