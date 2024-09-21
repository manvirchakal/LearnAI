import React, { useState, useEffect } from 'react';
import { Box, Typography, Paper, InputBase, Divider, IconButton, Collapse, CircularProgress } from '@mui/material';
import Sidebar from '../components/Sidebar';
import SendIcon from '@mui/icons-material/Send';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import axios from 'axios';
import styles from '../styles/Study.module.css'; // Import the CSS module
import { MathJaxContext, MathJax } from 'better-react-mathjax';
import Prism from 'prismjs';
import 'prismjs/themes/prism.css';
import ErrorBoundary from '../components/ErrorBoundary';
import DynamicGameComponent from '../components/DynamicGameComponent';

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

const formatSummary = (content) => {
  return content
    // Format main headings
    .replace(/^### (.*?)$/gm, '<h2 class="main-heading">$1</h2>')
    // Format subheadings
    .replace(/^## (.*?)$/gm, '<h3 class="sub-heading">$1</h3>')
    // Format sub-subheadings
    .replace(/^# (.*?)$/gm, '<h4 class="sub-sub-heading">$1</h4>')
    // Format lists
    .replace(/^- (.*?)$/gm, '<li>$1</li>')
    .replace(/<li>.*?<\/li>/gs, '<ul class="summary-list">$&</ul>')
    // Format paragraphs
    .replace(/^(?!<h[2-4]|<ul)(.*?)$/gm, '<p class="summary-paragraph">$1</p>')
    // Format bold text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    // Format italic text
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    // Format inline math
    .replace(/\$(.*?)\$/g, '<span class="inline-math">$$$1$$</span>')
    // Remove empty paragraphs
    .replace(/<p class="summary-paragraph">\s*<\/p>/g, '')
    // Add section dividers
    .replace(/<h2 class="main-heading">/g, '<hr class="section-divider"><h2 class="main-heading">');
};

const Study = () => {
  const [chapter, setChapter] = useState(null);
  const [section, setSection] = useState(null);
  const [message, setMessage] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [narrative, setNarrative] = useState('');
  const [gameIdea, setGameIdea] = useState('');
  const [gameCode, setGameCode] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [chatExpanded, setChatExpanded] = useState(false);
  const [isNarrativeLoading, setIsNarrativeLoading] = useState(false);

  // Modify fetchChapter to handle loading state
  const fetchChapter = async (chapterId) => {
    try {
      setIsNarrativeLoading(true);
      const chapterResponse = await axios.get(`/chapters/${chapterId}`);
      
      console.log("Fetched chapter data:", chapterResponse.data);
      setChapter(chapterResponse.data);
      setSection(chapterResponse.data.sections.length > 0 ? chapterResponse.data.sections[0] : null);
      
      // Fetch narrative asynchronously
      fetchNarrative(chapterId);
    } catch (error) {
      console.error('Error fetching chapter:', error);
      setNarrative('Failed to load narrative. Please try again.');
      setGameIdea('');
      setGameCode('');
      setIsNarrativeLoading(false);
    }
  };

  // New function to fetch narrative separately
  const fetchNarrative = async (chapterId) => {
    try {
      setIsNarrativeLoading(true);
      const response = await axios.get(`/generate-narrative/${chapterId}`);
      console.log("Fetched narrative:", response.data);
      
      setNarrative(response.data.narrative);
      setGameIdea(response.data.game_idea);
      setGameCode(response.data.game_code);
    } catch (error) {
      console.error('Error fetching narrative:', error);
      setNarrative('Failed to load narrative. Please try again.');
      setGameIdea('');
      setGameCode('');
    } finally {
      setIsNarrativeLoading(false);
    }
  };

  // Modify fetchSection similarly
  const fetchSection = async (sectionId) => {
    try {
      setIsNarrativeLoading(true);
      const sectionResponse = await axios.get(`/sections/${sectionId}`);
      
      console.log("Fetched section data:", sectionResponse.data);
      setSection(sectionResponse.data);
      setChapter(prevChapter => ({
        ...prevChapter,
        content: sectionResponse.data.content
      }));
      
      // Fetch narrative asynchronously
      fetchNarrative(sectionResponse.data.chapter_id);
    } catch (error) {
      console.error('Error fetching section:', error);
      setNarrative('Failed to load narrative. Please try again.');
      setGameIdea('');
      setGameCode('');
      setIsNarrativeLoading(false);
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

  // Use effect to render LaTeX when narrative changes
  useEffect(() => {
    if (narrative && window.MathJax) {
      window.MathJax.typesetPromise();
    }
  }, [narrative]);

  useEffect(() => {
    Prism.highlightAll();
  }, [narrative]);

  return (
    <MathJaxContext>
      <Box display="flex" height="100vh" overflow="hidden">
        <Sidebar onChapterSelect={handleChapterSelect} onSectionSelect={handleSectionSelect} setOpen={setSidebarOpen} />
        <Box 
          display="flex" 
          flexDirection="column" 
          flexGrow={1} 
          p={2} 
          ml={sidebarOpen ? '240px' : '60px'} 
          transition="margin-left 0.3s ease"
          overflow="auto"
        >
          <Box display="flex" mb={2}>
            <Typography variant="h4" flex={1}>
              {chapter ? `${chapter.title} > ${section?.title || 'Chapter Content'}` : 'Loading...'}
            </Typography>
            <Typography variant="h4" flex={1}>
              Summary
            </Typography>
          </Box>
          <Box display="flex" flexDirection="row" mb={2}>
            {/* Left Pane: Chapter Content */}
            <Box display="flex" flexDirection="column" flex={1} marginRight={2}>
              <Paper elevation={3} sx={{ p: 2, maxHeight: '60vh', overflowY: 'auto' }}>
                {(chapter && chapter.content) && (
                  <div className={styles.chapterContent} dangerouslySetInnerHTML={{ __html: preprocessLatex(chapter.content) }} />
                )}
                {(section && section.content && !chapter.content) && (
                  <div className={styles.chapterContent} dangerouslySetInnerHTML={{ __html: preprocessLatex(section.content) }} />
                )}
              </Paper>
            </Box>
            {/* Right Pane: Summary */}
            <Box display="flex" flexDirection="column" flex={1}>
              <Paper elevation={3} sx={{ p: 2, maxHeight: '60vh', overflowY: 'auto' }}>
                {isNarrativeLoading ? (
                  <Box display="flex" justifyContent="center" alignItems="center" height="100%">
                    <CircularProgress />
                  </Box>
                ) : narrative ? (
                  <MathJax>
                    <div 
                      className={styles.chapterContent} 
                      dangerouslySetInnerHTML={{ __html: formatSummary(preprocessLatex(narrative)) }} 
                    />
                  </MathJax>
                ) : (
                  <Typography>No summary available.</Typography>
                )}
              </Paper>
            </Box>
          </Box>
          
          {/* Interactive Game Component */}
          {gameCode && (
            <ErrorBoundary>
              <Paper elevation={3} sx={{ p: 2, mt: 2, mb: 2 }}>
                <Typography variant="h6">Interactive Game:</Typography>
                <DynamicGameComponent gameCode={gameCode} />
              </Paper>
            </ErrorBoundary>
          )}
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
    </MathJaxContext>
  );
};

export default Study;
