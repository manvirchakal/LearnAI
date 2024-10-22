import React from 'react';
import { Link } from 'react-router-dom';
import './NavBar.css';
import { FaFileUpload, FaBook, FaHome, FaQuestion } from 'react-icons/fa'; // Import FaBook icon
import logo from '../static/logo.png'; // Adjust the path to your actual logo file

const NavBar = () => {
  return (
    <header className="navbar">
      <div className="logo-container">
        <Link to="/">
          <img src={logo} alt="LearnAI logo" className="logo-img" style={{ width: '100px', height: 'auto' }} />
        </Link>
      </div>
      <nav>
        <ul className="nav-links">
          <li>
            <Link to="/">
              Home <FaHome style={{ marginLeft: '5px' }} />
            </Link>
          </li>
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
            <li>
            <Link to="/questionnaire">
              Questionnaire <FaQuestion style={{ marginLeft: '5px' }} />
            </Link>
          </li>
          <li>
            <Link to="/home" className="sign-up-btn">Sign up</Link>
          </li>
        </ul>
      </nav>
    </header>
  );
};

export default NavBar;
