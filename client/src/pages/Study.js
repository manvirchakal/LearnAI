import React, { useState, useEffect } from 'react';
import { Box, Typography, Paper, InputBase, Divider, IconButton, Button, Collapse } from '@mui/material';
import Sidebar from '../components/Sidebar';
import SendIcon from '@mui/icons-material/Send';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import axios from 'axios';

// Set the base URL for Axios
axios.defaults.baseURL = 'http://localhost:8000'; // Replace with your backend server URL

const Study = () => {
  const [textbookId, setTextbookId] = useState(1); // Example textbook ID
  const [chapters, setChapters] = useState([]);
  const [chapter, setChapter] = useState(null);
  const [section, setSection] = useState(null);
  const [message, setMessage] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [emotionAlert, setEmotionAlert] = useState(null);
  const [narrative, setNarrative] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [chatExpanded, setChatExpanded] = useState(false);

  // WebSocket connection for emotion detection
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/emotion');

    ws.onopen = () => {
      console.log("WebSocket connection established.");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("Raw WebSocket message received:", event.data);
        console.log("Parsed emotion received:", data.emotion);

        if (data.emotion === 'angry') {
          setEmotionAlert('Angry emotion detected! Please take a break.');
        } else {
          setEmotionAlert(null);  // Reset the alert if the emotion is not angry
        }
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error occurred:", error);
    };

    ws.onclose = (event) => {
      console.log("WebSocket connection closed. Reason:", event.reason);
    };

    return () => {
      console.log("Cleaning up WebSocket connection.");
      ws.close();
    };
  }, []);

  // Fetch chapters by textbook ID
  useEffect(() => {
    const fetchChapters = async () => {
      try {
        const response = await axios.get(`/textbooks/${textbookId}/chapters/`);
        console.log("Fetched chapters:", response.data);
        setChapters(response.data);
        if (response.data.length > 0) {
          fetchChapter(response.data[0].id); // Fetch the first chapter by default
        }
      } catch (error) {
        console.error('Error fetching chapters:', error);
      }
    };

    fetchChapters();
  }, [textbookId]);

  // Fetch chapter by chapter ID
  const fetchChapter = async (chapterId) => {
    try {
      const response = await axios.get(`/chapters/${chapterId}`);
      console.log("Fetched chapter data:", response.data);
      setChapter(response.data);
      setSection(response.data.sections.length > 0 ? response.data.sections[0] : null); // Automatically load the first section if available
    } catch (error) {
      console.error('Error fetching chapter:', error);
    }
  };

  // Fetch section by section ID
  const fetchSection = async (sectionId) => {
    try {
      const response = await axios.get(`/sections/${sectionId}`);
      console.log("Fetched section data:", response.data);
      setSection(response.data);
    } catch (error) {
      console.error('Error fetching section:', error);
    }
  };

  // Handle chapter selection from the sidebar
  const handleChapterSelect = (chapterId) => {
    fetchChapter(chapterId);
  };

  // Handle section selection from the sidebar
  const handleSectionSelect = (sectionId) => {
    fetchSection(sectionId);
  };

  // Fetch narrative for the current chapter
  const fetchNarrative = async () => {
    try {
      const chapterId = chapter ? chapter.id : 1; // Use the current chapter's ID if available
      setNarrative('Loading narrative...');
      const response = await axios.get(`/generate-narrative/${chapterId}`);
      console.log("Fetched narrative:", response.data);
      setNarrative(response.data.narrative);
    } catch (error) {
      console.error('Error fetching narrative:', error);
      if (error.response) {
        console.error('Error data:', error.response.data);
        console.error('Error status:', error.response.status);
        console.error('Error headers:', error.response.headers);
        setNarrative(`Failed to load narrative. Server responded with status ${error.response.status}. Please try again.`);
      } else if (error.request) {
        console.error('Error request:', error.request);
        setNarrative('Failed to load narrative. No response received from server. Please check your connection and try again.');
      } else {
        console.error('Error message:', error.message);
        setNarrative(`Failed to load narrative. Error: ${error.message}. Please try again.`);
      }
    }
  };

  // Handle sending a message
  const handleSendMessage = async (event) => {
    event.preventDefault();
    
    if (!message.trim()) return;

    try {
      const response = await axios.post('/api/chat', { message });
      console.log("Sent message:", message);
      console.log("AI response received:", response.data.reply);
      setChatMessages([...chatMessages, { user: 'You', text: message }, { user: 'AI', text: response.data.reply }]);
      setMessage('');
    } catch (error) {
      console.error('Error sending message:', error);
    }
  };

  const toggleChat = () => {
    setChatExpanded(!chatExpanded);
  };

  return (
    <Box display="flex" height="100vh">
      <Sidebar onChapterSelect={handleChapterSelect} onSectionSelect={handleSectionSelect} setOpen={setSidebarOpen} />
      <Box display="flex" flexDirection="column" flexGrow={1} p={2} ml={sidebarOpen ? '240px' : '60px'} transition="margin-left 0.3s ease">
        <Typography variant="h4" gutterBottom>
          {chapter ? `${chapter.title} > ${section?.title || 'Chapter Content'}` : 'Loading...'}
        </Typography>
        {emotionAlert && (
          <Typography variant="h6" color="error" gutterBottom>
            {emotionAlert}
          </Typography>
        )}
        <Box display="flex" flexDirection="row" flexGrow={1}>
          {/* Left Pane: Chapter Content */}
          <Box display="flex" flexDirection="column" flex={1} marginRight={2}>
            <Paper elevation={3} sx={{ p: 2, flex: 1, overflowY: 'auto' }}>
              <Typography variant="body1">
                {section ? section.content : chapter ? chapter.content : 'Loading content...'}
              </Typography>
            </Paper>
          </Box>
          {/* Right Pane: Generated Narrative */}
          <Box display="flex" flexDirection="column" flex={1}>
            <Paper elevation={3} sx={{ p: 2, flex: 1, overflowY: 'auto', mb: 2 }}>
              <Button variant="contained" color="primary" onClick={fetchNarrative}>
                Generate Narrative
              </Button>
              {narrative && (
                <Box mt={2}>
                  <Typography variant="h6">Generated Narrative:</Typography>
                  <Typography variant="body1">{narrative}</Typography>
                </Box>
              )}
            </Paper>
          </Box>
        </Box>
        {/* Webcam feed container */}
        <Box 
          sx={{ 
            position: 'absolute', 
            top: 10, 
            right: 10, 
            width: 200, 
            height: 150, 
            border: '2px solid black', 
            overflow: 'hidden'
          }}
        >
          <iframe 
            src="http://localhost:8000/webcam_feed"
            width="100%" 
            height="100%" 
            title="Webcam Feed"
            style={{ 
              border: 'none', 
              objectFit: 'contain', 
              maxWidth: '100%', 
              maxHeight: '100%'
            }}
          />
        </Box>
      </Box>
      {/* Chat Section */}
      <Box 
        sx={{ 
          position: 'fixed',
          bottom: 0,
          right: 0,
          width: '300px',
          height: chatExpanded ? '50%' : '60px',
          transition: 'height 0.3s ease',
          bgcolor: 'background.paper',
          boxShadow: 3,
          display: 'flex',
          flexDirection: 'column',
          zIndex: 1000,
        }}
      >
        <Box 
          onClick={toggleChat} 
          sx={{ 
            p: 1, 
            display: 'flex', 
            alignItems: 'center', 
            cursor: 'pointer',
            bgcolor: 'primary.main',
            color: 'white'
          }}
        >
          <Typography variant="h6" flexGrow={1}>Chat</Typography>
          <IconButton size="small" sx={{ color: 'white' }}>
            {chatExpanded ? <ExpandMoreIcon /> : <ExpandLessIcon />}
          </IconButton>
        </Box>
        <Collapse in={chatExpanded} sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ p: 2, flexGrow: 1, overflowY: 'auto' }}>
            {chatMessages.map((msg, index) => (
              <Typography key={index} variant="body2">
                <strong>{msg.user}: </strong>{msg.text}
              </Typography>
            ))}
          </Box>
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
        </Collapse>
      </Box>
    </Box>
  );
};

export default Study;
