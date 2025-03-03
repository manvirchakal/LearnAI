import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import './NavBar.css';
import { FaFileUpload, FaBook, FaHome, FaQuestion } from 'react-icons/fa';
import logo from '../static/logo.png';
import { useAuthenticator } from '@aws-amplify/ui-react';

const NavBar = () => {
  const location = useLocation();
  const { signOut } = useAuthenticator((context) => [context.signOut]);
  
  const handleSignOut = async () => {
    try {
      await signOut();
      window.location.href = '/';
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  return (
    <header className="navbar">
      <div className="logo-container">
        <Link to="/home">
          <img src={logo} alt="LearnAI logo" className="logo-img" style={{ width: '125px', height: 'auto' }} />
        </Link>
      </div>
      <nav>
        <ul className="nav-links">
          <li>
            <Link to="/home" className={location.pathname === '/home' ? 'active' : ''}>
              Home <FaHome style={{ marginLeft: '5px' }} />
            </Link>
          </li>
          <li>
            <Link to="/upload" className={location.pathname === '/upload' ? 'active' : ''}>
              Material Upload <FaFileUpload style={{ marginLeft: '5px' }} />
            </Link>
          </li>
          <li>
            <Link to="/select-textbook" className={location.pathname === '/select-textbook' ? 'active' : ''}>
              Library <FaBook style={{ marginLeft: '5px' }} />
            </Link>
          </li>
          <li>
            <Link to="/questionnaire" className={location.pathname === '/questionnaire' ? 'active' : ''}>
              Questionnaire <FaQuestion style={{ marginLeft: '5px' }} />
            </Link>
          </li>
          <li>
            <Link to="/study" className={location.pathname === '/study' ? 'active' : ''}>
              Study <FaBook style={{ marginLeft: '5px' }} />
            </Link>
          </li>
          <li>
            <button onClick={handleSignOut} className="sign-out-btn">Sign out</button>
          </li>
        </ul>
      </nav>
    </header>
  );
};

export default NavBar;
