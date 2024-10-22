import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Auth } from 'aws-amplify';
import { Box, Typography, List, ListItem, ListItemText, Button, CircularProgress } from '@mui/material';
import NavBar from './NavBar';

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
      const session = await Auth.currentSession();
      const token = session.getIdToken().getJwtToken();
      const response = await axios.get('/user-textbooks', {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      setTextbooks(response.data);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching textbooks:', err);
      setError('Failed to fetch textbooks');
      setLoading(false);
    }
  };

  const handleSelectTextbook = async (s3Key, title) => {
    try {
      console.log("Selected textbook S3 key:", s3Key);
      const session = await Auth.currentSession();
      const token = session.getIdToken().getJwtToken();
      const userId = session.getIdToken().payload.sub; // Get the user ID from the token

      // Split the S3 key into its components
      const [, , fileIdAndName] = s3Key.split('/');
      const [fileId, ...fileNameParts] = fileIdAndName.split('_');
      const fileName = fileNameParts.join('_');

      const response = await axios.get(`/textbook-structure/${userId}/${fileId}/${encodeURIComponent(fileName)}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      console.log("Textbook structure:", response.data);
      
      navigate('/study', { 
        state: { 
          bookStructure: response.data,
          s3Key: s3Key,
          title: title,
          file_id: fileId,
          filename: fileName,
          userId: userId
        } 
      });
    } catch (error) {
      console.error("Error fetching textbook structure:", error);
      // Handle the error appropriately
    }
  };

  if (loading) return (
    <>
      <NavBar />
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    </>
  );
  if (error) return (
    <>
      <NavBar />
      <Typography color="error">{error}</Typography>
    </>
  );

  return (
    <>
      <NavBar />
      <Box sx={{ maxWidth: 600, margin: 'auto', mt: 4 }}>
        <Typography variant="h4" gutterBottom>Select a Textbook</Typography>
      {textbooks.length === 0 ? (
        <Typography>No textbooks found. Please upload a textbook first.</Typography>
        ) : (
          <List>
            {textbooks.map((textbook, index) => (
              <ListItem 
                key={index} 
                button 
                onClick={() => handleSelectTextbook(textbook.s3_key, textbook.title)}
                sx={{ border: '1px solid #ddd', borderRadius: 1, mb: 1 }}
              >
                <ListItemText 
                  primary={textbook.title} 
                  secondary={`Uploaded on: ${textbook.upload_date}`} 
                />
              </ListItem>
            ))}
          </List>
        )}
        <Button variant="contained" onClick={() => navigate('/upload')} sx={{ mt: 2 }}>
          Upload New Textbook
        </Button>
      </Box>
    </>
  );
};

export default SelectTextbook;
