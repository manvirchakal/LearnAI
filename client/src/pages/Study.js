import React, { useState, useEffect } from 'react';
import { Box, Typography, Paper, InputBase, Divider, IconButton, Button, Collapse } from '@mui/material';
import Sidebar from '../components/Sidebar';
import SendIcon from '@mui/icons-material/Send';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import axios from 'axios';
import styles from '../styles/Study.module.css'; // Import the CSS module
import MathJax from 'react-mathjax';

// Set the base URL for Axios
axios.defaults.baseURL = 'http://localhost:8000';

// Add this function inside your component file, but outside of the component function
const preprocessLatex = (content) => {
  return content
    // Preserve LaTeX math environments
    .replace(/\\\[/g, '<div class="equation">\\[')
    .replace(/\\\]/g, '\\]</div>')
    .replace(/\$\$(.*?)\$\$/g, '<div class="equation">$$$$1$$</div>')
    
    // Handle inline math
    .replace(/\\\((.*?)\\\)/g, '<span class="inline-math">\\($1\\)</span>')
    .replace(/\$(.*?)\$/g, '<span class="inline-math">$$1$</span>')
    
    // Text formatting
    .replace(/\\textit{([^}]*)}/g, '<i>$1</i>')
    .replace(/\\textbf{([^}]*)}/g, '<strong>$1</strong>')
    .replace(/\\emph{([^}]*)}/g, '<em>$1</em>')
    
    // Spacing
    .replace(/\\quad/g, '&nbsp;&nbsp;&nbsp;&nbsp;')
    .replace(/\\qquad/g, '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;')
    
    // Sections
    .replace(/\\section{([^}]*)}/g, '<h2>$1</h2>')
    .replace(/\\subsection{([^}]*)}/g, '<h3>$1</h3>')
    
    // Lists
    .replace(/\\begin{itemize}([\s\S]*?)\\end{itemize}/g, '<ul>$1</ul>')
    .replace(/\\begin{enumerate}([\s\S]*?)\\end{enumerate}/g, '<ol>$1</ol>')
    .replace(/\\item\s/g, '<li>')
    
    // Paragraphs
    .replace(/\n\n/g, '</p><p>')
    
    // Wrap content in paragraphs
    .replace(/^(.|\n)*$/, '<p>$&</p>')
    
    // Clean up empty paragraphs
    .replace(/<p>\s*<\/p>/g, '')
    
    // Remove any remaining LaTeX commands
    .replace(/\\[a-zA-Z]+/g, '')
    
    // Clean up extra spaces
    .replace(/\s+/g, ' ')
    .trim();
};

const formatNarrative = (content) => {
  return content
    // Format headings
    .replace(/\*\*\*(.*?)\*\*\*/g, '<h2>$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, '<h3>$1</h3>')
    // Format definition lists
    .replace(/^(.*?):\s*$/gm, '<dt>$1</dt>')
    .replace(/^:\s*(.*?)$/gm, '<dd>$1</dd>')
    // Wrap definition lists
    .replace(/<dt>.*?<\/dd>/gs, match => `<dl>${match}</dl>`)
    // Format numbered lists
    .replace(/^\d+\.\s*(.*?)$/gm, '<li>$1</li>')
    .replace(/<li>.*?<\/li>/gs, match => `<ol>${match}</ol>`)
    // Format bullet lists
    .replace(/^-\s*(.*?)$/gm, '<li>$1</li>')
    .replace(/<li>.*?<\/li>/gs, match => `<ul>${match}</ul>`)
    // Format paragraphs (excluding list items and definition terms/descriptions)
    .replace(/^(?!<[oud]l|<li|<d[td])(.*?)$/gm, '<p>$1</p>')
    // Format inline math
    .replace(/\$([^$]+)\$/g, '<span class="inline-math">\\($1\\)</span>')
    // Format block math
    .replace(/\$\$([\s\S]*?)\$\$/g, '<div class="equation">\\[$1\\]</div>')
    // Format italic text
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    // Remove empty paragraphs
    .replace(/<p>\s*<\/p>/g, '')
    // Clean up extra spaces
    .replace(/\s+/g, ' ')
    .trim();
};

const Study = () => {
  const [chapter, setChapter] = useState(null);
  const [section, setSection] = useState(null);
  const [message, setMessage] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [narrative, setNarrative] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [chatExpanded, setChatExpanded] = useState(false);

  // Fetch chapter by chapter ID
  const fetchChapter = async (chapterId) => {
    try {
      const response = await axios.get(`/chapters/${chapterId}`);
      console.log("Fetched chapter data:", response.data);
      setChapter(response.data);
      setSection(response.data.sections.length > 0 ? response.data.sections[0] : null);
    } catch (error) {
      console.error('Error fetching chapter:', error);
    }
  };

  // Use effect to render LaTeX when chapter content changes
  useEffect(() => {
    if (chapter && window.MathJax) {
      window.MathJax.typesetPromise();
    }
  }, [chapter]);

  // Fetch section by section ID
  const fetchSection = async (sectionId) => {
    try {
      const response = await axios.get(`/sections/${sectionId}`);
      console.log("Fetched section data:", response.data);
      setSection(response.data);
      setChapter(prevChapter => ({
        ...prevChapter,
        content: response.data.content
      }));
    } catch (error) {
      console.error('Error fetching section:', error);
    }
  };

  // Handle chapter selection from the sidebar
  const handleChapterSelect = (chapterId) => {
    setSection(null);
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
    <Box display="flex" height="100vh" overflow="hidden">
      <Sidebar onChapterSelect={handleChapterSelect} onSectionSelect={handleSectionSelect} setOpen={setSidebarOpen} />
      <Box 
        display="flex" 
        flexDirection="column" 
        flexGrow={1} 
        p={2} 
        ml={sidebarOpen ? '240px' : '60px'} 
        transition="margin-left 0.3s ease"
        overflow="hidden"
      >
        <Typography variant="h4" gutterBottom>
          {chapter ? `${chapter.title} > ${section?.title || 'Chapter Content'}` : 'Loading...'}
        </Typography>
        <Box display="flex" flexDirection="row" flexGrow={1} overflow="hidden">
          {/* Left Pane: Chapter Content */}
          <Box display="flex" flexDirection="column" flex={1} marginRight={2} overflow="hidden">
            <Paper elevation={3} sx={{ p: 2, flex: 1, overflowY: 'auto', maxHeight: 'calc(100vh - 150px)' }}>
              {(chapter && chapter.content) && (
                <div className={styles.chapterContent} dangerouslySetInnerHTML={{ __html: preprocessLatex(chapter.content) }} />
              )}
              {(section && section.content && !chapter.content) && (
                <div className={styles.chapterContent} dangerouslySetInnerHTML={{ __html: preprocessLatex(section.content) }} />
              )}
            </Paper>
          </Box>
          {/* Right Pane: Generated Narrative */}
          <Box display="flex" flexDirection="column" flex={1} overflow="hidden">
            <Paper elevation={3} sx={{ p: 2, flex: 1, overflowY: 'auto', maxHeight: 'calc(100vh - 150px)' }}>
              <Button variant="contained" color="primary" onClick={fetchNarrative}>
                Generate Narrative
              </Button>
              {narrative && (
                <Box mt={2}>
                  <Typography variant="h6">Generated Narrative:</Typography>
                  <div className={styles.chapterContent} dangerouslySetInnerHTML={{ __html: formatNarrative(narrative) }} />
                </Box>
              )}
            </Paper>
          </Box>
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
