// Talks to GET/POST /api/v1/collections/{id}/chat — the ReAct agent
// (services/agent/chat_agent.py). History loads once on mount; each send
// appends an optimistic user bubble immediately (the agent can take a few
// seconds to run its tool loop) and reconciles with the real persisted
// messages once the response comes back.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import apiClient from '../../api/client';

const ChatPanel = ({ collectionId }) => {
  const [messages, setMessages] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await apiClient.get(`/api/v1/collections/${collectionId}/chat`);
        if (!cancelled) setMessages(data);
      } catch (err) {
        console.error('Error loading chat history:', err);
        if (!cancelled) setError('Failed to load chat history.');
      } finally {
        if (!cancelled) setLoadingHistory(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [collectionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const handleSend = useCallback(
    async (event) => {
      event.preventDefault();
      const text = input.trim();
      if (!text || sending) return;

      const optimisticId = `pending-${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        {
          id: optimisticId,
          seq: -1,
          role: 'user',
          content: text,
          citations: [],
          created_at: new Date().toISOString(),
        },
      ]);
      setInput('');
      setSending(true);
      setError(null);

      try {
        const { data } = await apiClient.post(`/api/v1/collections/${collectionId}/chat`, {
          message: text,
        });
        setMessages((prev) => [...prev, data]);
      } catch (err) {
        console.error('Error sending chat message:', err);
        setError(err.response?.data?.detail || 'Failed to send the message.');
        setMessages((prev) => prev.filter((m) => m.id !== optimisticId));
        setInput(text);
      } finally {
        setSending(false);
      }
    },
    [collectionId, input, sending]
  );

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: 500 }}>
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          border: '1px solid #eee',
          borderRadius: 1,
          p: 2,
          mb: 2,
        }}
      >
        {loadingHistory ? (
          <Box display="flex" justifyContent="center" mt={4}>
            <CircularProgress size={20} />
          </Box>
        ) : messages.length === 0 ? (
          <Typography color="text.secondary">
            Ask a question about this collection's materials.
          </Typography>
        ) : (
          <Stack spacing={2}>
            {messages.map((message) => (
              <Box
                key={message.id}
                sx={{
                  alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '80%',
                }}
              >
                <Box
                  sx={{
                    bgcolor: message.role === 'user' ? 'primary.main' : 'grey.100',
                    color: message.role === 'user' ? 'primary.contrastText' : 'text.primary',
                    borderRadius: 2,
                    px: 2,
                    py: 1,
                  }}
                >
                  <Typography sx={{ whiteSpace: 'pre-wrap' }}>{message.content}</Typography>
                </Box>
                {message.citations?.length > 0 && (
                  <Stack direction="row" spacing={0.5} sx={{ mt: 0.5, flexWrap: 'wrap' }}>
                    {message.citations.map((citation, index) => (
                      <Chip
                        key={`${citation.material_id}-${citation.node_id}-${index}`}
                        size="small"
                        label={`${citation.title} · p.${citation.page}`}
                        variant="outlined"
                      />
                    ))}
                  </Stack>
                )}
              </Box>
            ))}
            {sending && (
              <Box display="flex" alignItems="center" gap={1}>
                <CircularProgress size={16} />
                <Typography color="text.secondary" variant="body2">
                  Thinking…
                </Typography>
              </Box>
            )}
            <div ref={bottomRef} />
          </Stack>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box component="form" onSubmit={handleSend} sx={{ display: 'flex', gap: 1 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Ask about this collection…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={sending}
        />
        <Button type="submit" variant="contained" disabled={sending || !input.trim()}>
          Send
        </Button>
      </Box>
    </Box>
  );
};

export default ChatPanel;
