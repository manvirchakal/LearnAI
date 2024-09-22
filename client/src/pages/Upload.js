import React, { useEffect, useState } from 'react';
import { FaFileUpload } from 'react-icons/fa'; // Import upload icon
import NavBar from './NavBar'; // Import NavBar component
import './Upload.css'; // Import the CSS for styling
import { Auth } from 'aws-amplify';
import { useNavigate } from 'react-router-dom';
import UploadTextbook from '../components/FileUpload';

const Upload = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    checkAuthState();
  }, []);

  async function checkAuthState() {
    try {
      await Auth.currentAuthenticatedUser();
      setIsAuthenticated(true);
    } catch (err) {
      setIsAuthenticated(false);
      navigate('/login');
    }
  }

  if (!isAuthenticated) {
    return null; // or a loading spinner
  }

  return (
    <>
      <NavBar /> {/* Add NavBar component */}
      <div className="upload-container">
        <h2>Upload your textbook here</h2>
        <UploadTextbook />
      </div>
    </>
  );
};

export default Upload;
