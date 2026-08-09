// Streams GET /api/v1/collections/{id}/narrative — the backend's SSE
// endpoint — via a raw fetch + ReadableStream rather than EventSource, so
// errors (an `event: error` block, sent after a 200 has already gone out —
// see routers/generation.py) get parsed the same way as ordinary chunks.
import React, { useCallback, useEffect, useState } from 'react';
import { Alert, Box, Button, CircularProgress, Typography } from '@mui/material';
import { API_BASE_URL } from '../../api/client';

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

  useEffect(() => {
    onText?.(text);
  }, [text, onText]);

  const generate = useCallback(async () => {
    setStarted(true);
    setStreaming(true);
    setError(null);
    setText('');
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
      {started && !streaming && text && (
        <Button size="small" onClick={generate} sx={{ mt: 2 }}>
          Regenerate
        </Button>
      )}
    </Box>
  );
};

export default NarrativePanel;
