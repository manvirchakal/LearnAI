import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Box, Typography, Paper, InputBase, Divider, IconButton, Collapse, CircularProgress, Select, MenuItem, Button } from '@mui/material';
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
import { useLocation, useNavigate } from 'react-router-dom';
import { Auth } from 'aws-amplify';
import RefreshIcon from '@mui/icons-material/Refresh';

// Set the base URL for Axios
axios.defaults.baseURL = 'http://localhost:8000';

// Add a request interceptor
axios.interceptors.request.use(
  config => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

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
  const location = useLocation();
  const navigate = useNavigate();
  const { bookStructure, s3Key, title, file_id, filename } = location.state || {};

  const [userId, setUserId] = useState(location.state?.userId || null);
  const [currentSection, setCurrentSection] = useState(null);
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
  const [pdfUrl, setPdfUrl] = useState(null);
  const [numPages, setNumPages] = useState(null);

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

      setOriginalNarrative(generatedNarrative);
      setGameIdea(gameIdea);
      setGameCode(gameCode);
      setDiagrams(diagramsResponse.data.diagrams || []);

      if (targetLanguage !== 'en') {
        const translatedText = await translateText(generatedNarrative, targetLanguage);
        setTranslatedNarrative(translatedText);
      } else {
        setTranslatedNarrative(generatedNarrative);
      }
    } catch (error) {
      console.error('Error fetching narrative or diagrams:', error);
      setOriginalNarrative('Failed to load narrative. Please try again.');
      setTranslatedNarrative('Failed to load narrative. Please try again.');
      setGameIdea('');
      setGameCode('');
      setDiagrams([]);
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
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [narrativeStatus, setNarrativeStatus] = useState('');

  const findSectionInBookStructure = (sectionId) => {
    for (const chapter of bookStructure.chapters) {
      for (const section of chapter.sections) {
        if (section.id === sectionId) {
          return { ...section, chapterTitle: chapter.title, chapterId: chapter.id };
        }
      }
    }
    return null;
  };

  const fetchAndSetPDF = async (sectionId) => {
    try {
      console.log('Fetching PDF:', { userId, file_id, filename, sectionId });
      const token = localStorage.getItem('authToken');
      if (!token) {
        throw new Error('No authentication token found');
      }
      const response = await axios.get(`/get-section-pdf/${userId}/${file_id}/${filename}/${sectionId}`, {
        responseType: 'blob',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const pdfBlob = new Blob([response.data], { type: 'application/pdf' });
      const pdfUrl = URL.createObjectURL(pdfBlob);
      setPdfUrl(pdfUrl);
    } catch (error) {
      console.error('Error fetching PDF:', error);
      setError('Failed to load PDF. Please try again.');
    }
  };

  const processPDFSection = async (userId, fileId, filename, sectionName) => {
    console.log('processPDFSection called with:', { userId, fileId, filename, sectionName });
    
    if (!userId || !fileId || !filename || !sectionName) {
      console.error('Missing required parameters:', { userId, fileId, filename, sectionName });
      throw new Error('Missing required parameters for processing PDF section');
    }

    const formData = new FormData();
    formData.append('user_id', userId);
    formData.append('file_id', fileId);
    formData.append('filename', filename);
    formData.append('section_name', sectionName);

    try {
      const response = await axios.post('/process-pdf-section', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      return response.data.extracted_text;
    } catch (error) {
      console.error('Error in processPDFSection:', error);
      throw error;
    }
  };

  const generateNarrative = async (extractedText, userId, fileId, startPage, endPage, forceRegenerate) => {
    console.log('Sending data to generate-narrative:', { userId, fileId, startPage, endPage, forceRegenerate });
    const response = await axios.post('/generate-narrative', {
      chapter_content: extractedText,
      user_id: userId,
      file_id: fileId,
      section_id: `${startPage}_${endPage}`,
      force_regenerate: forceRegenerate
    });

    return {
      narrative: response.data.narrative,
      gameIdea: response.data.game_idea,
      gameCode: response.data.game_code
    };
  };

  const generateDiagrams = async (extractedText, narrative) => {
    try {
      const token = await Auth.currentSession().then(session => session.getIdToken().getJwtToken());
      const response = await axios.post('/generate-diagrams', {
        chapter_content: extractedText,
        generated_summary: narrative,
      }, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      return response.data.diagrams || [];
    } catch (error) {
      console.error('Error generating diagrams:', error);
      return [];
    }
  };

  useEffect(() => {
    if (!userId || !file_id || !filename) {
      console.error('Missing required information');
      // Handle this error, maybe redirect to SelectTextbook page
      return;
    }

    console.log('Study component initialized with:', { userId, file_id, filename, title });
    
    // You can now use these values in your component
  }, [userId, file_id, filename, title]);

  const handleSectionSelect = async (sectionId) => {
    try {
      setIsLoading(true);
      setError(null);
      
      console.log('Handling section select:', { sectionId, userId, file_id, filename });

      if (!userId || !file_id || !filename) {
        console.error('Missing required information');
        setError('Missing required information to load section. Please try again.');
        return;
      }

      const foundSection = findSectionInBookStructure(sectionId);
      if (foundSection) {
        setCurrentSection(foundSection);
        
        await fetchAndSetPDF(sectionId);

        console.log('Current user ID:', userId);

        await processAndGenerateNarrative(
          userId, 
          file_id, 
          filename, 
          foundSection.title,
          false // forceRegenerate
        );
      } else {
        console.error('Section not found in book structure');
        setError('Failed to load section. Please try again.');
      }
    } catch (error) {
      console.error('Error in handleSectionSelect:', error);
      setError('An error occurred while loading the section. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const processAndGenerateNarrative = async (userId, fileId, filename, sectionName, forceRegenerate = false) => {
    console.log('processAndGenerateNarrative called with:', { userId, fileId, filename, sectionName, forceRegenerate });
    
    if (!userId) {
      console.error('userId is missing in processAndGenerateNarrative');
      setError('User ID is missing. Please try logging in again.');
      return;
    }

    try {
      setIsNarrativeLoading(true);
      setNarrativeStatus('Processing PDF...');
      console.log('Starting narrative generation process');

      // Step 1: Process PDF section
      console.log('Processing PDF section');
      const extractedText = await processPDFSection(userId, fileId, filename, sectionName);
      console.log('PDF section processed');

      setNarrativeStatus('Generating summary...');
      // Step 2: Generate narrative
      console.log('Generating narrative');
      const { narrative, gameIdea, gameCode } = await generateNarrative(extractedText, userId, fileId, sectionName, forceRegenerate);
      console.log('Narrative generated');

      setOriginalNarrative(narrative);
      setGameIdea(gameIdea);
      setGameCode(gameCode);

      if (targetLanguage !== 'en') {
        setNarrativeStatus('Translating summary...');
        console.log('Translating narrative');
        const translatedText = await translateText(narrative, targetLanguage);
        setTranslatedNarrative(translatedText);
        console.log('Narrative translated');
      } else {
        setTranslatedNarrative(narrative);
      }

      setNarrativeStatus('Generating diagrams...');
      console.log('Generating diagrams');
      // Fetch diagrams
      const diagrams = await generateDiagrams(extractedText, narrative);
      setDiagrams(diagrams);
      console.log('Diagrams generated');

      setNarrativeStatus('');
    } catch (error) {
      console.error('Error in processAndGenerateNarrative:', error);
      setError('An error occurred while generating the narrative. Please try again.');
    } finally {
      setIsNarrativeLoading(false);
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

  useEffect(() => {
    if (bookStructure && bookStructure.chapters) {
      console.log("Book structure received:", bookStructure);
      // Set initial chapter and section if available
      if (bookStructure.chapters.length > 0) {
        setChapter(bookStructure.chapters[0]);
        if (bookStructure.chapters[0].sections && bookStructure.chapters[0].sections.length > 0) {
          setSection(bookStructure.chapters[0].sections[0]);
        }
      }
    } else {
      console.log("No book structure or chapters available");
    }
  }, [bookStructure]);

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
  };

  useEffect(() => {
    console.log("file_id in useEffect:", file_id);
    if (!file_id) {
      console.error("file_id is not available in the component state");
    }
  }, [file_id]);

  // Add this state variable
  const [isRegeneratingNarrative, setIsRegeneratingNarrative] = useState(false);

  // Add this function to handle narrative regeneration
  const handleRegenerateNarrative = async () => {
    if (!currentSection || !userId || !file_id || !filename) {
      console.error('Missing required information for regenerating narrative');
      setError('Missing required information to regenerate narrative. Please try again.');
      return;
    }

    try {
      setIsRegeneratingNarrative(true);
      await processAndGenerateNarrative(
        userId,
        file_id,
        filename,
        currentSection.title,
        true // forceRegenerate
      );
    } catch (error) {
      console.error('Error in handleRegenerateNarrative:', error);
      setError('An error occurred while regenerating the narrative. Please try again.');
    } finally {
      setIsRegeneratingNarrative(false);
    }
  };

  const handleSendMessage = async (event) => {
    event.preventDefault();
    if (!message.trim()) return;

    setIsGenerating(true);
    const userMessage = { user: 'You', text: message };
    setChatMessages(prevMessages => [...prevMessages, userMessage]);
    setMessage('');

    try {
      const response = await axios.post('/api/chat', {
        message: message,
        userId: userId,
        fileId: file_id,
        sectionName: currentSection.title,
        language: chatLanguage,
        forceRegenerate: isRegeneratingNarrative.toString() // Convert boolean to string
      });

      const aiMessage = { user: 'AI', text: response.data.reply };
      setChatMessages(prevMessages => [...prevMessages, aiMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      setChatMessages(prevMessages => [
        ...prevMessages,
        { user: 'AI', text: 'Sorry, I encountered an error. Please try again.' }
      ]);
    } finally {
      setIsGenerating(false);
    }
  };

  useEffect(() => {
    const updateContent = async () => {
      if (currentSection && userId && file_id && filename) {
        try {
          setIsLoading(true);
          setError(null);

          // Fetch the PDF for the selected section
          await fetchAndSetPDF(currentSection.id);

          console.log('Triggering narrative generation');
          // Generate narrative for the selected section
          await processAndGenerateNarrative(userId, file_id, filename, currentSection.title, false);

          // Update the chapter and section information
          setChapter(currentSection.chapter);
          setSection(currentSection);

          // Scroll to the top of the content
          window.scrollTo(0, 0);
        } catch (error) {
          console.error('Error updating content:', error);
          setError('An error occurred while loading the section content. Please try again.');
        } finally {
          setIsLoading(false);
        }
      } else {
        console.log('Missing required information to update content');
      }
    };

    updateContent();
  }, [currentSection, userId, file_id, filename]);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        await Auth.currentAuthenticatedUser();
      } catch (error) {
        console.error('User not authenticated', error);
        navigate('/login');
      }
    };
    checkAuth();
  }, []);

  useEffect(() => {
    const fetchUserData = async () => {
      if (!userId) {
        try {
          const user = await Auth.currentAuthenticatedUser();
          const currentUserId = user.attributes.sub; // or however you get the user ID from Cognito
          setUserId(currentUserId);
        } catch (error) {
          console.error('Error fetching user data:', error);
          navigate('/login');
        }
      }
    };

    fetchUserData();
  }, [userId, navigate]);

  return (
    <MathJaxContext>
      <Box display="flex" height="100vh" overflow="hidden">
        <Sidebar 
          onChapterSelect={handleChapterSelect} 
          onSectionSelect={handleSectionSelect} 
          setOpen={setSidebarOpen} 
          isOpen={sidebarOpen}
          bookStructure={bookStructure || { chapters: [] }}
          bookTitle={title}
          currentSection={currentSection?.id}
        />
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
              <Paper elevation={3} sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
                <Typography variant="h5" gutterBottom sx={{ fontWeight: 'bold', color: 'primary.main' }}>
                  {section && chapter 
                    ? `${chapter.title} - ${section.title}`
                    : chapter 
                      ? chapter.title
                      : 'No chapter selected'}
                </Typography>
                {pdfUrl ? (
                  <iframe
                    src={pdfUrl}
                    width="100%"
                    height="100%"
                    style={{ border: 'none', flexGrow: 1 }}
                    title="PDF Viewer"
                  />
                ) : (
                  chapter && chapter.content ? (
                    <MathJax>
                      <div className={styles.chapterContent} dangerouslySetInnerHTML={{ __html: preprocessLatex(chapter.content) }} />
                    </MathJax>
                  ) : section && section.content ? (
                    <MathJax>
                      <div className={styles.chapterContent} dangerouslySetInnerHTML={{ __html: preprocessLatex(section.content) }} />
                    </MathJax>
                  ) : (
                    <Typography>No content available.</Typography>
                  )
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
                    <Button
                      onClick={handleRegenerateNarrative}
                      disabled={isRegeneratingNarrative}
                      startIcon={<RefreshIcon />}
                      sx={{ mr: 2 }}
                    >
                      Regenerate Narrative
                    </Button>
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
                {isNarrativeLoading || isRegeneratingNarrative ? (
                  <Box display="flex" justifyContent="center" alignItems="center" height="100%">
                    <CircularProgress />
                  </Box>
                ) : translatedNarrative ? (
                  <Typography component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
                    {translatedNarrative}
                  </Typography>
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
                {diagrams.length > 0 ? (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, justifyContent: 'center' }}>
                    {diagrams.map((diagram, index) => (
                      <MermaidDiagram key={`diagram-${index}`} chart={diagram} />
                    ))}
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
