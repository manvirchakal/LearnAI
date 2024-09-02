// src/pages/Study.js
import React from 'react';
import { Box, Typography, Paper, InputBase, Divider, IconButton } from '@mui/material';
import Sidebar from '../components/Sidebar';
import SendIcon from '@mui/icons-material/Send';

const Study = () => {
  return (
    <Box display="flex" height="100vh">
      <Sidebar />
      <Box flexGrow={1} p={2} bgcolor="#F5F5F5" display="flex" flexDirection="column">
        <Typography variant="h6" color="primary" gutterBottom>
          Chapter Name > Section Name (Description of generated text/narrative)
        </Typography>
        <Box display="flex" flexDirection="row" flexGrow={1}>
          <Paper elevation={3} sx={{ p: 2, flex: 2, marginRight: 2 }}>
            <Typography variant="body1">
              Generated text...
            </Typography>
          </Paper>
          <Box display="flex" flexDirection="column" flex={1} height="100%">
            <Typography variant="h6" color="primary" gutterBottom>
              Chat
            </Typography>
            <Paper elevation={3} sx={{ p: 2, flexGrow: 1, marginBottom: 2 }}>
              {/* Chat messages will go here */}
            </Paper>
            <Divider />
            <Paper component="form" sx={{ p: '2px 4px', display: 'flex', alignItems: 'center' }}>
              <InputBase
                sx={{ ml: 1, flex: 1 }}
                placeholder="Enter message"
              />
              <IconButton type="submit" sx={{ p: '10px' }} aria-label="send">
                <SendIcon />
              </IconButton>
            </Paper>
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default Study;
