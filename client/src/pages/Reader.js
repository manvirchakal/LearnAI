// Browse a material's document tree and read a section — lazy extraction
// happens on the first request for a given node (see
// services/ingestion/pipeline.get_or_extract_section on the backend) and is
// cached after, so re-selecting a section is fast on every read but the
// first.
import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  List,
  ListItemButton,
  ListItemText,
  Typography,
} from '@mui/material';
import apiClient from '../api/client';
import NavBar from './NavBar';

const TreeItem = ({ node, activeNodeId, onSelect, depth }) => (
  <>
    <ListItemButton
      selected={node.node_id === activeNodeId}
      onClick={() => onSelect(node)}
      sx={{ pl: 2 + depth * 2 }}
    >
      <ListItemText
        primary={node.title}
        secondary={`p. ${node.start_page}–${node.end_page}`}
      />
    </ListItemButton>
    {node.nodes?.map((child) => (
      <TreeItem
        key={child.node_id}
        node={child}
        activeNodeId={activeNodeId}
        onSelect={onSelect}
        depth={depth + 1}
      />
    ))}
  </>
);

const Reader = () => {
  const { materialId } = useParams();
  const [material, setMaterial] = useState(null);
  const [tree, setTree] = useState(null);
  const [activeNode, setActiveNode] = useState(null);
  const [section, setSection] = useState(null);
  const [loadingSection, setLoadingSection] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setMaterial(null);
    setTree(null);
    setActiveNode(null);
    setSection(null);
    (async () => {
      try {
        const { data: materialData } = await apiClient.get(`/api/v1/materials/${materialId}`);
        if (cancelled) return;
        setMaterial(materialData);
        if (materialData.status === 'toc_ready') {
          const { data: treeData } = await apiClient.get(
            `/api/v1/materials/${materialId}/tree`
          );
          if (cancelled) return;
          setTree(treeData);
        }
      } catch (err) {
        console.error('Error loading material:', err);
        if (!cancelled) setError('Failed to load this material.');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [materialId]);

  const selectNode = async (node) => {
    setActiveNode(node);
    setSection(null);
    setLoadingSection(true);
    setError(null);
    try {
      const { data } = await apiClient.get(
        `/api/v1/materials/${materialId}/sections/${encodeURIComponent(node.node_id)}`
      );
      setSection(data);
    } catch (err) {
      console.error('Error extracting section:', err);
      setError(err.response?.data?.detail || 'Failed to load this section.');
    } finally {
      setLoadingSection(false);
    }
  };

  if (!material) {
    return (
      <>
        <NavBar />
        <Box display="flex" justifyContent="center" mt={8}>
          <CircularProgress />
        </Box>
      </>
    );
  }

  if (material.status !== 'toc_ready') {
    return (
      <>
        <NavBar />
        <Box sx={{ maxWidth: 600, margin: 'auto', mt: 6, px: 2 }}>
          <Typography variant="h5" gutterBottom>
            {material.filename}
          </Typography>
          {material.status === 'toc_failed' ? (
            <Alert severity="error">
              {material.error || 'Table of contents extraction failed.'}
            </Alert>
          ) : (
            <Box display="flex" alignItems="center" gap={1}>
              <CircularProgress size={20} />
              <Typography>Still building the table of contents…</Typography>
            </Box>
          )}
          <Box sx={{ mt: 3 }}>
            <Link to="/upload">Back to materials</Link>
          </Box>
        </Box>
      </>
    );
  }

  const citedPages = section
    ? [...new Set(section.citations.map((c) => c.start_page))].sort((a, b) => a - b)
    : [];

  return (
    <>
      <NavBar />
      <Box sx={{ display: 'flex', mt: 2, px: 2, gap: 3 }}>
        <Box sx={{ width: 300, flexShrink: 0 }}>
          <Typography variant="h6" gutterBottom noWrap title={material.filename}>
            {material.filename}
          </Typography>
          <List dense>
            {tree?.tree.map((node) => (
              <TreeItem
                key={node.node_id}
                node={node}
                activeNodeId={activeNode?.node_id}
                onSelect={selectNode}
                depth={0}
              />
            ))}
          </List>
        </Box>
        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          {!activeNode && (
            <Typography color="text.secondary">
              Select a section from the table of contents.
            </Typography>
          )}
          {loadingSection && (
            <Box display="flex" alignItems="center" gap={1}>
              <CircularProgress size={20} />
              <Typography color="text.secondary">Extracting section…</Typography>
            </Box>
          )}
          {section && !loadingSection && (
            <Box>
              <Typography variant="h5" gutterBottom>
                {activeNode.title}
              </Typography>
              {citedPages.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  {citedPages.map((page) => (
                    <Chip key={page} label={`p. ${page}`} size="small" sx={{ mr: 0.5 }} />
                  ))}
                </Box>
              )}
              <Typography sx={{ whiteSpace: 'pre-wrap' }}>{section.text}</Typography>
            </Box>
          )}
        </Box>
      </Box>
    </>
  );
};

export default Reader;
