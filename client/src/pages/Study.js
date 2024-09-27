import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Box, Typography, Paper, InputBase, Divider, IconButton, Collapse, CircularProgress, Select, MenuItem } from '@mui/material';
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
import MicIcon from '@mui/icons-material/Mic';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import VolumeUpIcon from '@mui/icons-material/VolumeUp';
import StopIcon from '@mui/icons-material/Stop';
import Webcam from 'react-webcam';
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
  const [targetLanguage, setTargetLanguage] = useState('en');
  const [originalNarrative, setOriginalNarrative] = useState('');
  const [translatedNarrative, setTranslatedNarrative] = useState('');
  const [chatLanguage, setChatLanguage] = useState('en');
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speechSynthesis, setSpeechSynthesis] = useState(null);
  const [diagrams, setDiagrams] = useState([]);
  const [emotion, setEmotion] = useState(null);
  const [webcamExpanded, setWebcamExpanded] = useState(false);
  const webcamRef = useRef(null);

  const messagesEndRef = useRef(null);
  const audioRef = useRef(null);

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

  const fetchNarrative = useCallback(async (chapterId, chapterContent) => {
    try {
      setIsNarrativeLoading(true);
      
      // Fetch narrative and game idea
      const narrativeResponse = await axios.post(`/generate-narrative/${chapterId}`, {
        chapter_content: chapterContent,
      });
      
      console.log("Fetched narrative:", narrativeResponse.data);
      
      const generatedNarrative = narrativeResponse.data.narrative;
      const gameIdea = narrativeResponse.data.game_idea;
      const gameCode = narrativeResponse.data.game_code;
  
      // Fetch diagrams using both chapter content and generated narrative
      const diagramsResponse = await axios.post(`/generate-diagrams`, {
        chapter_content: chapterContent,
        generated_summary: generatedNarrative,
      });
  
      console.log("Fetched diagrams:", diagramsResponse.data);
  
      // Combine narrative and diagrams
      let combinedNarrative = generatedNarrative;
      if (diagramsResponse.data.diagrams && diagramsResponse.data.diagrams.length > 0) {
        combinedNarrative += '\n\n### Concept Diagrams\n\n';
        diagramsResponse.data.diagrams.forEach((diagram, index) => {
          combinedNarrative += `\n\`\`\`mermaid\n${diagram}\n\`\`\`\n`;
        });
      }
  
      setOriginalNarrative(combinedNarrative);
      setGameIdea(gameIdea);
      setGameCode(gameCode);
  
      if (targetLanguage !== 'en') {
        const translatedText = await translateText(combinedNarrative, targetLanguage);
        setTranslatedNarrative(translatedText);
      } else {
        setTranslatedNarrative(combinedNarrative);
      }
    } catch (error) {
      console.error('Error fetching narrative or diagrams:', error);
      setOriginalNarrative('Failed to load narrative. Please try again.');
      setTranslatedNarrative('Failed to load narrative. Please try again.');
      setGameIdea('');
      setGameCode('');
    } finally {
      setIsNarrativeLoading(false);
    }
  }, [targetLanguage]);

  const translateText = async (text, targetLang) => {
    try {
      const response = await axios.post('/translate', {
        text: text,
        target_language: targetLang
      });
      return response.data.translated_text;
    } catch (error) {
      console.error('Error translating text:', error);
      return text; // Return original text if translation fails
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
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (message.trim() === '' || isGenerating) return;

    setIsGenerating(true);
    const newMessage = { user: 'You', text: message };
    setChatMessages(prevMessages => [...prevMessages, newMessage]);
    setMessage('');

    try {
      const response = await axios.post('/api/chat', {
        message: message,
        chapter_id: chapter?.id,
        chat_history: chatMessages,
        chapter_content: chapter?.content || '',
        language: chatLanguage,
        emotion: emotion
      });

      const aiResponse = response.data.reply;
      setChatMessages(prevMessages => [
        ...prevMessages,
        { user: 'AI', text: aiResponse }
      ]);

      // Speak the AI's response
      speakText(aiResponse);

    } catch (error) {
      console.error('Error sending message:', error);
      setChatMessages(prevMessages => [
        ...prevMessages,
        { user: 'AI', text: 'Sorry, there was an error processing your request.' }
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

  const handleLanguageChange = async (event) => {
    const newLanguage = event.target.value;
    setTargetLanguage(newLanguage);
    setChatLanguage(newLanguage);
    if (newLanguage === 'en') {
      setTranslatedNarrative(originalNarrative);
    } else {
      setIsNarrativeLoading(true);
      const translatedText = await translateText(originalNarrative, newLanguage);
      setTranslatedNarrative(translatedText);
      setIsNarrativeLoading(false);
    }
  };

  useEffect(() => {
    if (window.MathJax) {
      window.MathJax.typesetPromise().then(() => {
        console.log('MathJax typesetting complete');
      }).catch((err) => console.error('MathJax typesetting failed:', err));
    }
  }, [translatedNarrative]);

  const handleSpeechRecognition = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.error("Speech recognition not supported in this browser");
      return;
    }

    const recognitionInstance = new SpeechRecognition();
    recognitionInstance.lang = chatLanguage;
    recognitionInstance.continuous = false;
    recognitionInstance.interimResults = false;

    recognitionInstance.onstart = () => {
      setIsListening(true);
    };

    recognitionInstance.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setMessage(transcript);
    };

    recognitionInstance.onerror = (event) => {
      console.error('Speech recognition error', event.error);
      setIsListening(false);
    };

    recognitionInstance.onend = () => {
      setIsListening(false);
    };

    setRecognition(recognitionInstance);

    if (isListening) {
      recognitionInstance.stop();
    } else {
      recognitionInstance.start();
    }
  };

  const speakText = async (text) => {
    if (isSpeaking) {
      setIsSpeaking(false);
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
      return;
    }

    try {
      const response = await axios.post('/api/synthesize-speech', 
        { text, language: chatLanguage },
        { responseType: 'blob' }
      );

      const audioBlob = new Blob([response.data], { type: 'audio/mpeg' });
      const audioUrl = URL.createObjectURL(audioBlob);

      if (audioRef.current) {
        audioRef.current.src = audioUrl;
        audioRef.current.play();
        setIsSpeaking(true);
      }
    } catch (error) {
      console.error('Error synthesizing speech:', error);
    }
  };

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = '';
      }
    };
  }, []);
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

  // const captureAndDetectEmotion = async () => {
  //   if (webcamRef.current) {
  //     const imageSrc = webcamRef.current.getScreenshot();
  //     const blob = await fetch(imageSrc).then(r => r.blob());
  //     const formData = new FormData();
  //     formData.append('file', blob, 'emotion.jpg');

  //     try {
  //       const response = await axios.post('/api/detect-emotion', formData, {
  //         headers: { 'Content-Type': 'multipart/form-data' }
  //       });
  //       setEmotion(response.data.emotion);
  //     } catch (error) {
  //       console.error('Error detecting emotion:', error);
  //     }
  //   }
  // };

  useEffect(() => {
    //const intervalId = setInterval(captureAndDetectEmotion, 5000); // Detect every 5 seconds
    //return () => clearInterval(intervalId);
  }, []);

  const toggleWebcam = () => {
    setWebcamExpanded(!webcamExpanded);
  };

  const renderContent = (content) => {
    const paragraphs = content.split('\n');
    const regularContent = [];
    const diagramContent = [];

    let inMermaidBlock = false;
    let currentDiagram = '';
    let currentList = null;
    let diagramIndex = 0;

    paragraphs.forEach((paragraph, index) => {
      if (paragraph.trim() === '```mermaid') {
        inMermaidBlock = true;
        currentDiagram = '';
      } else if (paragraph.trim() === '```' && inMermaidBlock) {
        inMermaidBlock = false;
        diagramContent.push(
          <MermaidDiagram key={`diagram-${index}`} chart={currentDiagram.trim()} />
        );
        diagramIndex++;
      } else if (inMermaidBlock) {
        currentDiagram += paragraph + '\n';
      } else {
        // Check for headings and subheadings
        if (paragraph.startsWith('***')) {
          regularContent.push(
            <Typography key={`heading-${index}`} variant="h4" gutterBottom sx={{ mt: 4, mb: 2, color: 'primary.main' }}>
              {paragraph.replace(/^\*\*\*\s*/, '')}
            </Typography>
          );
          currentList = null;
        } else if (paragraph.startsWith('**')) {
          regularContent.push(
            <Typography key={`subheading-${index}`} variant="h5" gutterBottom sx={{ mt: 3, mb: 1, color: 'secondary.main' }}>
              {paragraph.replace(/^\*\*\s*/, '')}
            </Typography>
          );
          currentList = null;
        } else if (paragraph.match(/^\d+\./)) {
          // Numbered list item
          if (!currentList) {
            currentList = [];
            regularContent.push(
              <ol key={`list-${index}`} style={{ paddingLeft: '20px' }}>
                {currentList}
              </ol>
            );
          }
          currentList.push(
            <li key={`item-${index}`}>
              <MathJax>
                <div dangerouslySetInnerHTML={{ __html: preprocessLatex(paragraph.replace(/^\d+\.\s*/, '')) }} />
              </MathJax>
            </li>
          );
        } else if (paragraph.startsWith('-')) {
          // Bullet point
          regularContent.push(
            <Box key={`bullet-${index}`} sx={{ display: 'flex', alignItems: 'flex-start', mb: 1 }}>
              <Typography sx={{ mr: 1 }}>•</Typography>
              <MathJax>
                <div dangerouslySetInnerHTML={{ __html: preprocessLatex(paragraph.replace(/^-\s*/, '')) }} />
              </MathJax>
            </Box>
          );
          currentList = null;
        } else {
          // Regular paragraph
          regularContent.push(
            <Typography key={`paragraph-${index}`} paragraph>
              <MathJax>
                <div dangerouslySetInnerHTML={{ __html: preprocessLatex(paragraph) }} />
              </MathJax>
            </Typography>
          );
          currentList = null;
        }
      }
    });

    return { regularContent, diagramContent };
  };

  return (
    <MathJaxContext>
      <Box display="flex" height="100vh" overflow="hidden">
        <Sidebar onChapterSelect={handleChapterSelect} onSectionSelect={handleSectionSelect} setOpen={setSidebarOpen} isOpen={sidebarOpen} />
        <Box 
          display="flex" 
          flexDirection="column" 
          flexGrow={1} 
          p={2} 
          ml={sidebarOpen ? '240px' : '60px'} 
          transition="margin-left 0.3s ease"
          height="100%"
        >
          {/* Top row: Chapter Content and Summary */}
          <Box display="flex" height="50%" mb={2}>
            {/* Top Left: Chapter Content */}
            <Box flex={1} mr={1}>
              <Paper elevation={3} sx={{ p: 2, height: '100%', overflowY: 'auto' }}>
                <Typography variant="h5" gutterBottom sx={{ fontWeight: 'bold', color: 'primary.main' }}>
                  {chapter ? chapter.title : (section ? `${section.chapter_title}: ${section.title}` : 'No chapter selected')}
                </Typography>
                {chapter && chapter.content ? (
                  <MathJax>
                    <div className={styles.chapterContent} dangerouslySetInnerHTML={{ __html: preprocessLatex(chapter.content) }} />
                  </MathJax>
                ) : section && section.content ? (
                  <MathJax>
                    <div className={styles.chapterContent} dangerouslySetInnerHTML={{ __html: preprocessLatex(section.content) }} />
                  </MathJax>
                ) : (
                  <Typography>No content available.</Typography>
                )}
              </Paper>
            </Box>
            {/* Top Right: Summary */}
            <Box flex={1} ml={1}>
              <Paper elevation={3} sx={{ p: 2, height: '100%', overflowY: 'auto' }}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h5" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
                    Summary
                  </Typography>
                  <Box display="flex" alignItems="center">
                    <Typography variant="body2" sx={{ mr: 1 }}>Language:</Typography>
                    <Select
                      value={targetLanguage}
                      onChange={handleLanguageChange}
                      sx={{ minWidth: 120 }}
                      size="small"
                    >
                      <MenuItem value="en">English</MenuItem>
                      <MenuItem value="es">Spanish</MenuItem>
                      <MenuItem value="fr">French</MenuItem>
                      <MenuItem value="de">German</MenuItem>
                      <MenuItem value="zh">Chinese</MenuItem>
                    </Select>
                  </Box>
                </Box>
                {isNarrativeLoading ? (
                  <Box display="flex" justifyContent="center" alignItems="center" height="100%">
                    <CircularProgress />
                  </Box>
                ) : translatedNarrative ? (
                  <div className={styles.chapterContent}>
                    {renderContent(translatedNarrative).regularContent}
                  </div>
                ) : (
                  <Typography>No summary available.</Typography>
                )}
              </Paper>
            </Box>
          </Box>
          
          {/* Bottom row: Concept Diagrams and Interactive Game */}
          <Box display="flex" height="50%">
            {/* Bottom Left: Concept Diagrams */}
            <Box flex={1} mr={1}>
              <Paper elevation={3} sx={{ p: 2, height: '100%', overflowY: 'auto' }}>
                <Typography variant="h6" gutterBottom>Concept Diagrams</Typography>
                {translatedNarrative && renderContent(translatedNarrative).diagramContent.length > 0 ? (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, justifyContent: 'center' }}>
                    {renderContent(translatedNarrative).diagramContent}
                  </Box>
                ) : (
                  <Typography>No diagrams available.</Typography>
                )}
              </Paper>
            </Box>
            {/* Bottom Right: Interactive Game */}
            <Box flex={1} ml={1}>
              <Paper elevation={3} sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                <Typography variant="h6" gutterBottom>Interactive Game</Typography>
                <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
                  {gameCode ? (
                    <ErrorBoundary>
                      <DynamicGameComponent gameCode={gameCode} />
                    </ErrorBoundary>
                  ) : (
                    <Typography>No game available for this chapter.</Typography>
                  )}
                </Box>
              </Paper>
            </Box>
          </Box>
        </Box>

        
          {/* Chat Section (unchanged) */}
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
                        mx: 'auto',
                        position: 'relative',
                      }}
                    >
                      <Typography variant="body2" sx={{ fontWeight: 'bold', color: msg.user === 'You' ? 'text.primary' : 'white' }}>
                        {msg.user}:
                      </Typography>
                      <Typography variant="body2" sx={{ color: msg.user === 'You' ? 'text.primary' : 'white', pr: 4 }}>
                        {msg.text}
                      </Typography>
                      {msg.user === 'AI' && (
                        <IconButton 
                          onClick={() => speakText(msg.text)} 
                          sx={{ 
                            color: 'white',
                            position: 'absolute',
                            right: 8,
                            top: 8,
                            backgroundColor: 'rgba(255, 255, 255, 0.3)',
                            '&:hover': {
                              backgroundColor: 'rgba(255, 255, 255, 0.5)',
                            },
                          }}
                        >
                          {isSpeaking ? <StopIcon /> : <VolumeUpIcon />}
                        </IconButton>
                      )}
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
                    disabled={isGenerating || isListening}
                  />
                  <IconButton onClick={handleSpeechRecognition} sx={{ p: '10px' }} aria-label="transcribe">
                    <MicIcon color={isListening ? "secondary" : "primary"} />
                  </IconButton>
                  <IconButton type="submit" sx={{ p: '10px' }} aria-label="send" disabled={isGenerating || isListening}>
                    {isGenerating ? <CircularProgress size={24} /> : <SendIcon />}
                  </IconButton>
                </Paper>
              </Box>
            )}
          </Box>
          <audio ref={audioRef} onEnded={() => setIsSpeaking(false)} />
          <Box
            sx={{
              position: 'fixed',
              top: 10,
              right: 0,
              width: webcamExpanded ? '320px' : '60px',
              height: webcamExpanded ? '240px' : '60px',
              transition: 'all 0.3s ease',
              bgcolor: 'background.paper',
              boxShadow: 3,
              display: 'flex',
              flexDirection: 'column',
              zIndex: 1000,
              overflow: 'hidden',
            }}
          >
            <Box
              onClick={toggleWebcam}
              sx={{
                p: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                bgcolor: 'primary.main',
                color: 'white',
                height: '60px',
              }}
            >
              <IconButton size="small" sx={{ color: 'white' }}>
                {webcamExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>
            <Box sx={{ display: webcamExpanded ? 'block' : 'none' }}>
              <Webcam
                audio={false}
                ref={webcamRef}
                screenshotFormat="image/jpeg"
                videoConstraints={{ width: 320, height: 240, facingMode: "user" }}
                style={{ width: '100%', height: '180px' }}
              />
              {emotion && (
                <Typography variant="body2" sx={{ p: 1, textAlign: 'center' }}>
                  Detected emotion: {emotion}
                </Typography>
              )}
            </Box>
          </Box>
        </Box>
    </MathJaxContext>
  );
};

export default Study;
