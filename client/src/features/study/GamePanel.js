import React, { useCallback, useState } from 'react';
import { Alert, Box, Button, CircularProgress, Typography } from '@mui/material';
import apiClient from '../../api/client';
import GameFrame from '../../components/GameFrame';

const GamePanel = ({ collectionId }) => {
  const [game, setGame] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [score, setScore] = useState(null);

  const generate = useCallback(async () => {
    setLoading(true);
    setError(null);
    setScore(null);
    try {
      const { data } = await apiClient.post(`/api/v1/collections/${collectionId}/game`);
      setGame(data);
    } catch (err) {
      console.error('Error generating game:', err);
      setError(err.response?.data?.detail || 'Failed to generate a game.');
    } finally {
      setLoading(false);
    }
  }, [collectionId]);

  return (
    <Box>
      {!game && (
        <Button variant="contained" onClick={generate} disabled={loading}>
          {loading ? 'Generating…' : 'Generate a game'}
        </Button>
      )}
      {loading && (
        <Box display="flex" alignItems="center" gap={1} sx={{ mt: 1 }}>
          <CircularProgress size={20} />
          <Typography color="text.secondary">This can take a little while…</Typography>
        </Box>
      )}
      {error && (
        <Alert severity="error" sx={{ mt: 1 }}>
          {error}
        </Alert>
      )}
      {game && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="h6">{game.idea.title}</Typography>
          <Typography color="text.secondary" sx={{ mb: 1 }}>
            {game.code.instructions}
          </Typography>
          <GameFrame javascript={game.code.javascript} onComplete={setScore} />
          {score !== null && (
            <Alert severity="success" sx={{ mt: 1 }}>
              Nice work — score {Math.round(score * 100)}%
            </Alert>
          )}
          <Button size="small" onClick={() => setScore(null)} sx={{ mt: 2 }}>
            Play again
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default GamePanel;
