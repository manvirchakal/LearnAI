import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, Paper, InputBase, Divider, IconButton, Button, Collapse, CircularProgress } from '@mui/material';
import Sidebar from '../components/Sidebar';
import SendIcon from '@mui/icons-material/Send';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import axios from 'axios';
import styles from '../styles/Study.module.css'; // Import the CSS module
import { MathJaxContext, MathJax } from 'better-react-mathjax'

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
    .replace(/^(Key Concept:.*?)$/gm, '<h2>$1</h2>')
    .replace(/^\*(.*?)\*$/gm, '<h3>$1</h3>')
    // Format definition lists
    .replace(/^(.*?):\s*$/gm, '<dt>$1</dt>')
    .replace(/^:\s*(.*?)$/gm, '<dd>$1</dd>')
    // Wrap definition lists
    .replace(/<dt>.*?<\/dd>/gs, match => `<dl>${match}</dl>`)
    // Format numbered lists
    .replace(/^\d+\.\s*(.*?)$/gm, '<li>$1</li>')
    .replace(/(?<!<\/li>)\n<li>/g, '</li>\n<li>')
    .replace(/(<li>.*?<\/li>\n*)+/gs, match => `<ol>${match}</ol>`)
    // Format bullet lists
    .replace(/^-\s*(.*?)$/gm, '<li>$1</li>')
    .replace(/(?<!<\/li>)\n<li>/g, '</li>\n<li>')
    .replace(/(<li>.*?<\/li>\n*)+/gs, match => `<ul>${match}</ul>`)
    // Format paragraphs (excluding list items and definition terms/descriptions)
    .replace(/^(?!<[oud]l|<li|<d[td]|<h[23])(.*?)$/gm, '<p>$1</p>')
    // Format inline math
    .replace(/\\\((.*?)\\\)/g, '\\($1\\)')
    .replace(/\$(.*?)\$/g, '\\($1\\)')
    // Format block math
    .replace(/\\\[(.*?)\\\]/g, '\\[$1\\]')
    .replace(/\$\$(.*?)\$\$/g, '\\[$1\\]')
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
  const [isNarrativeLoading, setIsNarrativeLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [chatMessages]);

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
      setIsNarrativeLoading(false);
    }
  };

  // New function to fetch narrative separately
  const fetchNarrative = async (chapterId) => {
    try {
      const narrativeResponse = await axios.get(`/generate-narrative/${chapterId}`);
      console.log("Fetched narrative:", narrativeResponse.data);
      setNarrative(narrativeResponse.data.narrative);
    } catch (error) {
      console.error('Error fetching narrative:', error);
      setNarrative('Failed to load narrative. Please try again.');
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
        chapter_id: chapter.id
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
      window.MathJax.typesetPromise();
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
          overflow="hidden"
        >
          <Box display="flex" mb={2}>
            <Typography variant="h4" flex={1}>
              {chapter ? `${chapter.title} > ${section?.title || 'Chapter Content'}` : 'Loading...'}
            </Typography>
            <Typography variant="h4" flex={1}>
              Summary
            </Typography>
          </Box>
          <Box display="flex" flexDirection="row" flexGrow={1} overflow="hidden">
            {/* Left Pane: Chapter Content */}
            <Box display="flex" flexDirection="column" flex={1} marginRight={2} overflow="hidden">
              <Paper elevation={3} sx={{ p: 2, flex: 1, overflowY: 'auto', maxHeight: 'calc(100vh - 200px)' }}>
                {(chapter && chapter.content) && (
                  <div className={styles.chapterContent} dangerouslySetInnerHTML={{ __html: preprocessLatex(chapter.content) }} />
                )}
                {(section && section.content && !chapter.content) && (
                  <div className={styles.chapterContent} dangerouslySetInnerHTML={{ __html: preprocessLatex(section.content) }} />
                )}
              </Paper>
            </Box>
            {/* Right Pane: Summary */}
            <Box display="flex" flexDirection="column" flex={1} overflow="hidden">
              <Paper elevation={3} sx={{ p: 2, flex: 1, overflowY: 'auto', maxHeight: 'calc(100vh - 200px)' }}>
                {isNarrativeLoading ? (
                  <Box display="flex" justifyContent="center" alignItems="center" height="100%">
                    <CircularProgress />
                  </Box>
                ) : narrative ? (
                  <MathJax>
                    <div className={styles.chapterContent} dangerouslySetInnerHTML={{ __html: formatNarrative(narrative) }} />
                  </MathJax>
                ) : (
                  <Typography>No summary available.</Typography>
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
