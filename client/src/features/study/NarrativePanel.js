// Streams GET /api/v1/collections/{id}/narrative — the backend's SSE
// endpoint — via a raw fetch + ReadableStream rather than EventSource, so
// errors (an `event: error` block, sent after a 200 has already gone out —
// see routers/generation.py) get parsed the same way as ordinary chunks.
//
// Listen/Translate call the Phase 7 media endpoints directly on whatever
// text is currently shown (the translated text once there is one, so
// "Listen" after "Translate" reads the translation aloud).
import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  MenuItem,
  Select,
  Typography,
} from '@mui/material';
import apiClient, { API_BASE_URL } from '../../api/client';

const LANGUAGES = [
  { code: 'en-US', label: 'English' },
  { code: 'es-ES', label: 'Spanish' },
  { code: 'fr-FR', label: 'French' },
  { code: 'de-DE', label: 'German' },
];

function parseBlock(block) {
  const isError = block.startsWith('event: error');
  const dataLine = block.split('\n').find((line) => line.startsWith('data: '));
  if (!dataLine) return null;
  try {
    return { isError, payload: JSON.parse(dataLine.slice('data: '.length)) };
  } catch {
    return null;
  }
}

const NarrativePanel = ({ collectionId, onText }) => {
  const [text, setText] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [started, setStarted] = useState(false);
  const [error, setError] = useState(null);

  const [language, setLanguage] = useState('en-US');
  const [translatedText, setTranslatedText] = useState(null);
  const [translating, setTranslating] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [mediaError, setMediaError] = useState(null);

  useEffect(() => {
    onText?.(text);
  }, [text, onText]);

  const generate = useCallback(async () => {
    setStarted(true);
    setStreaming(true);
    setError(null);
    setText('');
    setTranslatedText(null);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/collections/${collectionId}/narrative`,
        { credentials: 'include' }
      );
      if (!response.ok || !response.body) {
        throw new Error(`request failed with status ${response.status}`);
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let done = false;
      while (!done) {
        const result = await reader.read();
        done = result.done;
        if (result.value) buffer += decoder.decode(result.value, { stream: true });
        const blocks = buffer.split('\n\n');
        buffer = blocks.pop() || '';
        for (const block of blocks) {
          const parsed = parseBlock(block);
          if (!parsed) continue;
          if (parsed.isError) {
            setError(parsed.payload.detail || 'The narrative generation failed.');
          } else if (parsed.payload.chunk) {
            setText((prev) => prev + parsed.payload.chunk);
          }
        }
      }
    } catch (err) {
      console.error('Error streaming narrative:', err);
      setError('Failed to generate the narrative.');
    } finally {
      setStreaming(false);
    }
  }, [collectionId]);

  const handleLanguageChange = (event) => {
    setLanguage(event.target.value);
    setTranslatedText(null);
  };

  const handleTranslate = useCallback(async () => {
    setMediaError(null);
    setTranslating(true);
    try {
      const { data } = await apiClient.post('/api/v1/media/translate', {
        text,
        target_language: language,
      });
      setTranslatedText(data.translated_text);
    } catch (err) {
      console.error('Error translating narrative:', err);
      setMediaError('Failed to translate this narrative.');
    } finally {
      setTranslating(false);
    }
  }, [text, language]);

  const handleListen = useCallback(async () => {
    setMediaError(null);
    setSpeaking(true);
    try {
      const response = await apiClient.post(
        '/api/v1/media/tts',
        { text: translatedText || text, language },
        { responseType: 'blob' }
      );
      const url = URL.createObjectURL(response.data);
      const audio = new Audio(url);
      audio.onended = () => URL.revokeObjectURL(url);
      await audio.play();
    } catch (err) {
      console.error('Error synthesizing speech:', err);
      setMediaError('No voice is available for this language.');
    } finally {
      setSpeaking(false);
    }
  }, [text, translatedText, language]);

  return (
    <Box>
      {!started && (
        <Button variant="contained" onClick={generate}>
          Generate narrative
        </Button>
      )}
      {streaming && !text && (
        <Box display="flex" alignItems="center" gap={1}>
          <CircularProgress size={20} />
          <Typography color="text.secondary">Writing…</Typography>
        </Box>
      )}
      {error && (
        <Alert severity="error" sx={{ mt: 1 }}>
          {error}
        </Alert>
      )}
      {text && <Typography sx={{ whiteSpace: 'pre-wrap', mt: 2 }}>{text}</Typography>}
      {translatedText && (
        <Typography sx={{ whiteSpace: 'pre-wrap', mt: 2, fontStyle: 'italic' }}>
          {translatedText}
        </Typography>
      )}

      {text && !streaming && (
        <Box sx={{ mt: 2, display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
          <Select size="small" value={language} onChange={handleLanguageChange}>
            {LANGUAGES.map((option) => (
              <MenuItem key={option.code} value={option.code}>
                {option.label}
              </MenuItem>
            ))}
          </Select>
          <Button size="small" onClick={handleListen} disabled={speaking}>
            {speaking ? 'Loading…' : 'Listen'}
          </Button>
          <Button
            size="small"
            onClick={handleTranslate}
            disabled={translating || language === 'en-US'}
          >
            {translating ? 'Translating…' : 'Translate'}
          </Button>
          <Button size="small" onClick={generate}>
            Regenerate
          </Button>
        </Box>
      )}
      {mediaError && (
        <Alert severity="warning" sx={{ mt: 1 }}>
          {mediaError}
        </Alert>
      )}
    </Box>
  );
};

export default NarrativePanel;
