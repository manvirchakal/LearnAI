import React, { useState, useEffect } from 'react';
import { Box, Typography, Paper, InputBase, Divider, IconButton } from '@mui/material';
import Sidebar from '../components/Sidebar';
import SendIcon from '@mui/icons-material/Send';
import axios from 'axios';

const Study = () => {
  const [chapter, setChapter] = useState(null);
  const [section, setSection] = useState(null);
  const [message, setMessage] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  
  // Fetch chapter and section data
  useEffect(() => {
    const fetchChapterData = async () => {
      try {
        const chapterId = 1; // Example chapter ID
        const response = await axios.get(`/chapters/${chapterId}`);
        setChapter(response.data);
        setSection(response.data.sections[0]); // Automatically load the first section
      } catch (error) {
        console.error('Error fetching chapter:', error);
      }
    };

    fetchChapterData();
  }, []);

  const handleSendMessage = async (event) => {
    event.preventDefault();
    
    if (!message.trim()) return;

    try {
      const response = await axios.post('/api/chat', { message });  // Replace with actual API endpoint
      setChatMessages([...chatMessages, { user: 'You', text: message }, { user: 'AI', text: response.data.reply }]);
      setMessage('');
    } catch (error) {
      console.error('Error sending message:', error);
    }
  };

  return (
    <Box display="flex" height="100vh">
      <Sidebar />
      <Box flexGrow={1} p={2} bgcolor="#F5F5F5" display="flex" flexDirection="column">
        <Typography variant="h6" color="primary" gutterBottom>
          {chapter ? `${chapter.title} > ${section?.title}` : 'Loading...'}
        </Typography>
        <Box display="flex" flexDirection="row" flexGrow={1}>
          <Paper elevation={3} sx={{ p: 2, flex: 2, marginRight: 2 }}>
            <Typography variant="body1">
              {section ? section.content : 'Loading content...'}
            </Typography>
          </Paper>
          <Box display="flex" flexDirection="column" flex={1} height="100%">
            <Typography variant="h6" color="primary" gutterBottom>
              Chat
            </Typography>
            <Paper elevation={3} sx={{ p: 2, flexGrow: 1, marginBottom: 2 }}>
              <Box sx={{ overflowY: 'auto', maxHeight: '400px' }}>
                {chatMessages.map((msg, index) => (
                  <Typography key={index} variant="body2">
                    <strong>{msg.user}: </strong>{msg.text}
                  </Typography>
                ))}
              </Box>
            </Paper>
            <Divider />
            <Paper component="form" sx={{ p: '2px 4px', display: 'flex', alignItems: 'center' }} onSubmit={handleSendMessage}>
              <InputBase
                sx={{ ml: 1, flex: 1 }}
                placeholder="Enter message"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
              />
              <IconButton type="submit" sx={{ p: '10px' }} aria-label="send">
                <SendIcon />
              </IconButton>
            </Paper>
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default Study;
