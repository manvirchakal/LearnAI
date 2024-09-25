import React, { useState, useEffect, useRef, useCallback } from 'react';
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
import MermaidDiagram from '../components/MermaidDiagram';

// Set the base URL for Axios
axios.defaults.baseURL = 'http://localhost:8000';

// Add this function inside your component file, but outside of the component function
const preprocessLatex = (content) => {
  if (typeof content !== 'string') {
    console.error('preprocessLatex received non-string content:', content);
    return '';
  }

  return content
    // Wrap display math in specific divs
    .replace(/\$\$(.*?)\$\$/g, '<div class="math-display">\\[$1\\]</div>')
    
    // Wrap inline math in specific spans
    .replace(/\$(.*?)\$/g, '<span class="math-inline">\\($1\\)</span>')
    
    // Other transformations...
    .replace(/\\textit{([^}]*)}/g, '<i>$1</i>')
    .replace(/\\textbf{([^}]*)}/g, '<strong>$1</strong>')
    .replace(/\\emph{([^}]*)}/g, '<em>$1</em>')
    
    // Clean up extra spaces
    .replace(/\s+/g, ' ')
    .trim();
};

const formatSummary = (content) => {
  let processedContent = content;
  
  // Store LaTeX equations temporarily
  const equations = [];
  processedContent = processedContent.replace(/\$\$(.*?)\$\$|\$(.*?)\$|\\\[(.*?)\\\]|\\\((.*?)\\\)/gs, (match) => {
    equations.push(match);
    return `%%EQUATION${equations.length - 1}%%`;
  });

  // Apply other transformations
  processedContent = processedContent
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
    // Add section dividers
    .replace(/<h2 class="main-heading">/g, '<hr class="section-divider"><h2 class="main-heading">')
    // Remove empty paragraphs
    .replace(/<p class="summary-paragraph">\s*<\/p>/g, '');

  // Restore LaTeX equations
  equations.forEach((eq, index) => {
    processedContent = processedContent.replace(`%%EQUATION${index}%%`, eq);
  });

  return processedContent;
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
  const [isGenerating, setIsGenerating] = useState(false);
  const [diagrams, setDiagrams] = useState([]);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [chatMessages]);

  // Modify fetchChapter to include chapter content in the narrative generation request
  const fetchChapter = async (chapterId) => {
    try {
      setIsNarrativeLoading(true);
      const chapterResponse = await axios.get(`/chapters/${chapterId}`);
      
      console.log("Fetched chapter data:", chapterResponse.data);
      setChapter(chapterResponse.data);
      setSection(chapterResponse.data.sections.length > 0 ? chapterResponse.data.sections[0] : null);
      
      // Fetch narrative with chapter content
      fetchNarrative(chapterId, chapterResponse.data.content);
    } catch (error) {
      console.error('Error fetching chapter:', error);
      setNarrative('Failed to load narrative. Please try again.');
      setGameIdea('');
      setGameCode('');
      setIsNarrativeLoading(false);
    }
  };

  // Modify fetchNarrative to include chapter content
  const fetchNarrative = async (chapterId, chapterContent) => {
    try {
      setIsNarrativeLoading(true);
      const response = await axios.post(`/generate-narrative/${chapterId}`, {
        chapter_content: chapterContent
      });
      console.log("Fetched narrative:", response.data);
      
      setNarrative(response.data.narrative);
      setGameIdea(response.data.game_idea);
      setGameCode(response.data.game_code);  // Make sure this line is present
      setDiagrams(response.data.diagrams);
    } catch (error) {
      console.error('Error fetching narrative:', error);
      setNarrative('Failed to load narrative. Please try again.');
      setGameIdea('');
      setGameCode('');  // Clear the game code on error
      setDiagrams([]);
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
      fetchNarrative(sectionResponse.data.chapter_id, sectionResponse.data.content);
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

  // Modify handleSendMessage to include chapter content in the chat request
  const handleSendMessage = async (event) => {
    event.preventDefault();
    
    if (!message.trim() || !chapter) return;

    const newUserMessage = { user: 'You', text: message };
    setChatMessages(prevMessages => [...prevMessages, newUserMessage]);
    const currentMessage = message;
    setMessage('');

    try {
      setIsGenerating(true);
      const response = await axios.post('/api/chat', {
        message: currentMessage,
        chat_history: chatMessages,
        chapter_id: chapter.id,
        chapter_content: chapter.content // Include chapter content in the request
      });

      if (response.data && response.data.reply) {
        setChatMessages(response.data.updated_chat_history);
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (error) {
      console.error('Error in chat:', error);
      setChatMessages(prevMessages => [
        ...prevMessages,
        { user: 'AI', text: `Sorry, an error occurred: ${error.message}. Please try again.` }
      ]);
    } finally {
      setIsGenerating(false);
    }
  };

  const toggleChat = () => {
    setChatExpanded(!chatExpanded);
  };

  // Use effect to render LaTeX when narrative changes
  useEffect(() => {
    if (narrative && window.MathJax) {
      window.MathJax.typesetPromise([document.querySelector('.chapterContent')])
        .then(() => {
          console.log('MathJax typesetting complete');
        })
        .catch((err) => console.error('MathJax typesetting failed:', err));
    }
  }, [narrative]);

  useEffect(() => {
    Prism.highlightAll();
  }, [narrative]);

  useEffect(() => {
    if ((chapter && chapter.content) || (section && section.content) || narrative) {
      if (window.MathJax) {
        window.MathJax.typesetPromise().then(() => {
          console.log('MathJax typesetting complete');
        }).catch((err) => console.error('MathJax typesetting failed:', err));
      }
    }
  }, [chapter, section, narrative]);

  useEffect(() => {
    if (narrative) {
      console.log("Raw narrative:", narrative);
      console.log("Processed narrative:", preprocessLatex(narrative));
    }
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
                  <MathJax key={narrative}>
                    <div className={styles.chapterContent} dangerouslySetInnerHTML={{ __html: preprocessLatex(chapter.content) }} />
                  </MathJax>
                )}
                {(section && section.content && !chapter.content) && (
                  <MathJax key={narrative}>
                    <div className={styles.chapterContent} dangerouslySetInnerHTML={{ __html: preprocessLatex(section.content) }} />
                  </MathJax>
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
                  <MathJax key={narrative}>
                    <div 
                      className={styles.chapterContent} 
                      dangerouslySetInnerHTML={{ __html: preprocessLatex(narrative) }} 
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
            <Typography variant="h6" color="white" flexGrow={1}>Chat</Typography>
            <IconButton size="small" sx={{ color: 'white' }}>
              {chatExpanded ? <ExpandMoreIcon /> : <ExpandLessIcon />}
            </IconButton>
          </Box>
          {chatExpanded && (
            <Box sx={{ display: 'flex', flexDirection: 'column', height: 'calc(100% - 48px)' }}>
              <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 2 }}>
                {chatMessages.map((msg, index) => (
                  <Box 
                    key={index} 
                    sx={{ 
                      mb: 2, 
                      p: 1, 
                      bgcolor: msg.user === 'You' ? 'grey.100' : 'primary.main', 
                      borderRadius: 1,
                      width: '90%',
                      mx: 'auto', // This centers the message box
                    }}
                  >
                    <Typography variant="body2" sx={{ fontWeight: 'bold', color: msg.user === 'You' ? 'text.primary' : 'white' }}>
                      {msg.user}:
                    </Typography>
                    <Typography variant="body2" sx={{ color: msg.user === 'You' ? 'text.primary' : 'white' }}>
                      {msg.text}
                    </Typography>
                  </Box>
                ))}
                <div ref={messagesEndRef} />
              </Box>
              <Divider />
              <Paper component="form" sx={{ p: '2px 4px', display: 'flex', alignItems: 'center' }} onSubmit={handleSendMessage}>
                <InputBase
                  sx={{ ml: 1, flex: 1 }}
                  placeholder="Enter message"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  disabled={isGenerating}
                />
                <IconButton type="submit" sx={{ p: '10px' }} aria-label="send" disabled={isGenerating}>
                  {isGenerating ? <CircularProgress size={24} /> : <SendIcon />}
                </IconButton>
              </Paper>
            </Box>
          )}
        </Box>
      </Box>
    </MathJaxContext>
  );
};

export default Study;
