import React from 'react';
import { Link } from 'react-router-dom';
import './NavBar.css';
import { FaFileUpload, FaBook } from 'react-icons/fa'; // Import FaBook icon
import logo from '../static/logo.png'; // Adjust the path to your actual logo file

const NavBar = () => {
  return (
    <header className="navbar">
      <div className="logo-container">
        <Link to="/">
          <img src={logo} alt="LearnAI logo" className="logo-img" />
        </Link>
      </div>
      <nav>
        <ul className="nav-links">
          <li><Link to="/">Home</Link></li>
          <li><Link to="/study">Study</Link></li>
          <li>
            <Link to="/upload">
              Textbook upload <FaFileUpload style={{ marginLeft: '5px' }} />
            </Link>
          </li>
          <li>
            <Link to="/select-textbook">
              Textbooks <FaBook style={{ marginLeft: '5px' }} />
            </Link>
          </li>
          <li><Link to="/questionnaire">Questionnaire</Link></li>
          <li>
            <Link to="/home" className="sign-up-btn">Sign up</Link>
          </li>
        </ul>
      </nav>
    </header>
  );
};

export default NavBar;
