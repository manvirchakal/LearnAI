// Real upload against POST /api/v1/materials — the old version's submit
// handlers only console.log'd (see the modernization plan's "Ingestion is
// dead" finding). Upload returns 202 with a job id; this polls the
// material's own status (which mirrors the job) every 2s until the TOC
// pass finishes, then makes it clickable into the reader.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  LinearProgress,
  List,
  ListItemButton,
  ListItemText,
  Typography,
} from '@mui/material';
import apiClient from '../api/client';
import NavBar from './NavBar';

const STATUS_LABEL = {
  uploaded: 'Queued',
  toc_processing: 'Extracting table of contents…',
  toc_ready: 'Ready',
  toc_failed: 'Failed',
};

const STATUS_COLOR = {
  uploaded: 'default',
  toc_processing: 'info',
  toc_ready: 'success',
  toc_failed: 'error',
};

const SETTLED_STATUSES = new Set(['toc_ready', 'toc_failed']);

const Upload = () => {
  const [materials, setMaterials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const navigate = useNavigate();
  const pollTimers = useRef(new Set());

  const fetchMaterials = useCallback(async () => {
    const { data } = await apiClient.get('/api/v1/materials');
    setMaterials(data);
    return data;
  }, []);

  const pollUntilSettled = useCallback((materialId) => {
    const poll = async () => {
      try {
        const { data } = await apiClient.get(`/api/v1/materials/${materialId}`);
        setMaterials((prev) => prev.map((m) => (m.id === materialId ? data : m)));
        if (!SETTLED_STATUSES.has(data.status)) {
          const timer = setTimeout(poll, 2000);
          pollTimers.current.add(timer);
        }
      } catch (err) {
        console.error('Error polling material status:', err);
      }
    };
    poll();
  }, []);

  useEffect(() => {
    const timers = pollTimers.current;
    (async () => {
      setLoading(true);
      try {
        const data = await fetchMaterials();
        data
          .filter((m) => !SETTLED_STATUSES.has(m.status))
          .forEach((m) => pollUntilSettled(m.id));
      } catch (err) {
        console.error('Error fetching materials:', err);
        setError('Failed to load your materials.');
      } finally {
        setLoading(false);
      }
    })();
    return () => {
      timers.forEach(clearTimeout);
    };
  }, [fetchMaterials, pollUntilSettled]);

  const handleFileSelected = async (event) => {
    const file = event.target.files[0];
    event.target.value = ''; // allow re-selecting the same file later
    if (!file) return;

    setError(null);
    setUploading(true);
    setUploadProgress(0);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const { data } = await apiClient.post('/api/v1/materials', formData, {
        onUploadProgress: (evt) => {
          if (evt.total) setUploadProgress(Math.round((evt.loaded / evt.total) * 100));
        },
      });
      await fetchMaterials();
      pollUntilSettled(data.material_id);
    } catch (err) {
      console.error('Error uploading material:', err);
      setError(err.response?.data?.detail || 'Failed to upload file.');
    } finally {
      setUploading(false);
    }
  };

  const openMaterial = (material) => {
    if (material.status === 'toc_ready') {
      navigate(`/materials/${material.id}`);
    }
  };

  return (
    <>
      <NavBar />
      <Box sx={{ maxWidth: 700, margin: 'auto', mt: 4, px: 2 }}>
        <Typography variant="h4" gutterBottom>
          Upload Materials
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Upload a PDF and we'll read it directly — no OCR — building a browsable table of
          contents in the background.
        </Typography>

        <Button variant="contained" component="label" disabled={uploading} sx={{ mb: 1 }}>
          {uploading ? `Uploading… ${uploadProgress}%` : 'Choose PDF'}
          <input type="file" accept="application/pdf" hidden onChange={handleFileSelected} />
        </Button>
        {uploading && (
          <LinearProgress variant="determinate" value={uploadProgress} sx={{ mb: 2 }} />
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Typography variant="h6" sx={{ mt: 4, mb: 1 }}>
          Your materials
        </Typography>
        {loading ? (
          <Box display="flex" justifyContent="center" mt={4}>
            <CircularProgress />
          </Box>
        ) : materials.length === 0 ? (
          <Typography>No materials yet. Upload a PDF above to get started.</Typography>
        ) : (
          <List>
            {materials.map((material) => (
              <ListItemButton
                key={material.id}
                onClick={() => openMaterial(material)}
                disabled={material.status !== 'toc_ready'}
                sx={{
                  border: '1px solid #ddd',
                  borderRadius: 1,
                  mb: 1,
                  display: 'flex',
                  justifyContent: 'space-between',
                }}
              >
                <ListItemText
                  primary={material.filename}
                  secondary={
                    material.status === 'toc_failed'
                      ? material.error || 'Extraction failed'
                      : material.page_count
                        ? `${material.page_count} pages`
                        : null
                  }
                />
                <Chip
                  size="small"
                  label={STATUS_LABEL[material.status] || material.status}
                  color={STATUS_COLOR[material.status] || 'default'}
                />
              </ListItemButton>
            ))}
          </List>
        )}
      </Box>
    </>
  );
};

export default Upload;
