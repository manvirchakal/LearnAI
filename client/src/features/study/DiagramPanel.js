import React, { useCallback, useState } from 'react';
import { Alert, Box, Button, CircularProgress, Typography } from '@mui/material';
import apiClient from '../../api/client';
import MermaidDiagram from '../../components/MermaidDiagram';

const DiagramPanel = ({ collectionId, narrative }) => {
  const [diagrams, setDiagrams] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const generate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.post(`/api/v1/collections/${collectionId}/diagrams`, {
        narrative: narrative || null,
      });
      setDiagrams(data.diagrams);
    } catch (err) {
      console.error('Error generating diagrams:', err);
      setError(err.response?.data?.detail || 'Failed to generate diagrams.');
    } finally {
      setLoading(false);
    }
  }, [collectionId, narrative]);

  return (
    <Box>
      {!diagrams && (
        <Button variant="contained" onClick={generate} disabled={loading}>
          {loading ? 'Generating…' : 'Generate diagrams'}
        </Button>
      )}
      {loading && (
        <Box display="flex" alignItems="center" gap={1} sx={{ mt: 1 }}>
          <CircularProgress size={20} />
          <Typography color="text.secondary">Sketching…</Typography>
        </Box>
      )}
      {error && (
        <Alert severity="error" sx={{ mt: 1 }}>
          {error}
        </Alert>
      )}
      {diagrams && diagrams.length === 0 && (
        <Typography color="text.secondary">No diagrams came back for this material.</Typography>
      )}
      {diagrams?.map((diagram, index) => (
        <Box key={diagram.title + index} sx={{ mt: 3 }}>
          <Typography variant="subtitle1" gutterBottom>
            {diagram.title}
          </Typography>
          <MermaidDiagram chart={diagram.mermaid} index={index} />
        </Box>
      ))}
      {diagrams && (
        <Button size="small" onClick={generate} sx={{ mt: 2 }} disabled={loading}>
          Regenerate
        </Button>
      )}
    </Box>
  );
};

export default DiagramPanel;
