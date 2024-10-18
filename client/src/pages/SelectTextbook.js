import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const SelectTextbook = () => {
  const [textbooks, setTextbooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchTextbooks();
  }, []);

  const fetchTextbooks = async () => {
    try {
      const response = await axios.get('/api/user-textbooks');
      setTextbooks(response.data);
      setLoading(false);
    } catch (err) {
      setError('Failed to fetch textbooks');
      setLoading(false);
    }
  };

  const handleSelectTextbook = (s3Key) => {
    // Navigate to the textbook viewer or set the selected textbook in state
    navigate(`/textbook/${encodeURIComponent(s3Key)}`);
  };

  if (loading) return <div>Loading textbooks...</div>;
  if (error) return <div>{error}</div>;

  return (
    <div className="select-textbook">
      <h2>Select a Textbook</h2>
      {textbooks.length === 0 ? (
        <p>No textbooks found. Please upload a textbook first.</p>
      ) : (
        <ul>
          {textbooks.map((textbook, index) => (
            <li key={index} onClick={() => handleSelectTextbook(textbook.s3_key)}>
              <h3>{textbook.title}</h3>
              <p>Uploaded on: {textbook.upload_date}</p>
            </li>
          ))}
        </ul>
      )}
      <button onClick={() => navigate('/upload')}>Upload New Textbook</button>
    </div>
  );
};

export default SelectTextbook;