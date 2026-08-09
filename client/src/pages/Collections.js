import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  Button,
  TextField,
  CircularProgress,
} from '@mui/material';
import apiClient from '../api/client';
import NavBar from './NavBar';

const Collections = () => {
  const navigate = useNavigate();
  const [collections, setCollections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);

  const fetchCollections = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get('/api/v1/collections');
      setCollections(data);
    } catch (err) {
      console.error('Error fetching collections:', err);
      setError('Failed to load collections.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCollections();
  }, []);

  const handleCreate = async (event) => {
    event.preventDefault();
    if (!newName.trim()) {
      return;
    }
    setCreating(true);
    setError(null);
    try {
      await apiClient.post('/api/v1/collections', { name: newName.trim(), kind: 'manual' });
      setNewName('');
      await fetchCollections();
    } catch (err) {
      console.error('Error creating collection:', err);
      setError('Failed to create collection.');
    } finally {
      setCreating(false);
    }
  };

  return (
    <>
      <NavBar />
      <Box sx={{ maxWidth: 600, margin: 'auto', mt: 4, px: 2 }}>
        <Typography variant="h4" gutterBottom>My Collections</Typography>

        <Box component="form" onSubmit={handleCreate} sx={{ display: 'flex', gap: 1, mb: 3 }}>
          <TextField
            label="New collection name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            size="small"
            fullWidth
          />
          <Button type="submit" variant="contained" disabled={creating || !newName.trim()}>
            {creating ? 'Creating…' : 'Create'}
          </Button>
        </Box>

        {error && <Typography color="error" sx={{ mb: 2 }}>{error}</Typography>}

        {loading ? (
          <Box display="flex" justifyContent="center" mt={4}>
            <CircularProgress />
          </Box>
        ) : collections.length === 0 ? (
          <Typography>No collections yet. Create one above to get started.</Typography>
        ) : (
          <List>
            {collections.map((collection) => (
              <ListItem
                key={collection.id}
                sx={{
                  border: '1px solid #ddd',
                  borderRadius: 1,
                  mb: 1,
                  display: 'flex',
                  justifyContent: 'space-between',
                }}
              >
                <ListItemText
                  primary={collection.name}
                  secondary={`${collection.kind} · ${collection.material_refs.length} material(s)`}
                />
                <Button
                  size="small"
                  disabled={collection.material_refs.length === 0}
                  onClick={() => navigate(`/study/${collection.id}`)}
                >
                  Study
                </Button>
              </ListItem>
            ))}
          </List>
        )}
      </Box>
    </>
  );
};

export default Collections;
