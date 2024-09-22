import React from 'react';
import ReactDOM from 'react-dom';
import './index.css';
import App from './App';
import { MathJaxContext } from 'better-react-mathjax';
//import './aws-config';

ReactDOM.render(
  <React.StrictMode>
    <MathJaxContext>
      <App />
    </MathJaxContext>
  </React.StrictMode>,
  document.getElementById('root')
);



// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
//reportWebVitals();
