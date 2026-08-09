// Collection-level generated study content: narrative (streamed), a
// sandboxed game, and diagrams — the routers/generation.py endpoints from
// the modernization plan's Phase 5. Panels stay mounted across tab
// switches (display:none rather than unmounting) so an in-flight
// narrative stream or an already-generated game isn't lost by tabbing away.
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Alert, Box, Tab, Tabs, Typography } from '@mui/material';
import apiClient from '../api/client';
import NavBar from './NavBar';
import NarrativePanel from '../features/study/NarrativePanel';
import GamePanel from '../features/study/GamePanel';
import DiagramPanel from '../features/study/DiagramPanel';

const Study = () => {
  const { collectionId } = useParams();
  const [collection, setCollection] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState(0);
  const [narrativeText, setNarrativeText] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await apiClient.get(`/api/v1/collections/${collectionId}`);
        if (!cancelled) setCollection(data);
      } catch (err) {
        console.error('Error loading collection:', err);
        if (!cancelled) setError('Failed to load this collection.');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [collectionId]);

  return (
    <>
      <NavBar />
      <Box sx={{ maxWidth: 900, margin: 'auto', mt: 4, px: 2 }}>
        <Typography variant="h4" gutterBottom>
          {collection?.name || 'Study'}
        </Typography>

        {error && <Alert severity="error">{error}</Alert>}

        <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 3 }}>
          <Tab label="Narrative" />
          <Tab label="Game" />
          <Tab label="Diagrams" />
        </Tabs>

        <Box sx={{ display: tab === 0 ? 'block' : 'none' }}>
          <NarrativePanel collectionId={collectionId} onText={setNarrativeText} />
        </Box>
        <Box sx={{ display: tab === 1 ? 'block' : 'none' }}>
          <GamePanel collectionId={collectionId} />
        </Box>
        <Box sx={{ display: tab === 2 ? 'block' : 'none' }}>
          <DiagramPanel collectionId={collectionId} narrative={narrativeText} />
        </Box>
      </Box>
    </>
  );
};

export default Study;
