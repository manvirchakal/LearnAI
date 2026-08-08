import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Box, Typography, List, ListItem, ListItemText, Button, CircularProgress } from '@mui/material';
import NavBar from './NavBar';

// This page predates the collections-based library (see pages/Collections.js)
// and still targets the old S3-keyed textbook endpoints, which no longer
// exist on the new backend — out of scope to rewrite here (that's the
// ingestion/materials work in a later phase). Only patched enough to drop
// the removed aws-amplify dependency and use the cookie-authenticated API
// client instead of a Cognito bearer token.
const SelectTextbook = () => {
  const [textbooks, setTextbooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    fetchTextbooks();
  }, []);

  const fetchTextbooks = async () => {
    try {
      const response = await apiClient.get('/user-textbooks');
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
      const userId = user?.id;

      // Split the S3 key into its components
      const [, , fileIdAndName] = s3Key.split('/');
      const [fileId, ...fileNameParts] = fileIdAndName.split('_');
      const fileName = fileNameParts.join('_');

      const response = await apiClient.get(
        `/textbook-structure/${userId}/${fileId}/${encodeURIComponent(fileName)}`
      );

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
                button={true}
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
