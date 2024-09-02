// src/components/Sidebar.js
import React, { useState } from 'react';
import { Drawer, List, ListItem, ListItemText, IconButton, Divider, Collapse, Box } from '@mui/material';
import { Home as HomeIcon, MenuBook as BookIcon, Person as PersonIcon, ExitToApp as ExitToAppIcon, ExpandLess, ExpandMore } from '@mui/icons-material';
import MenuIcon from '@mui/icons-material/Menu';

const Sidebar = () => {
  const [open, setOpen] = useState(false);
  const [bookOpen, setBookOpen] = useState(false);

  const toggleDrawer = () => {
    setOpen(!open);
  };

  const handleBookClick = () => {
    setBookOpen(!bookOpen);
  };

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      <Drawer
        variant="permanent"
        anchor="left"
        open={open}
        sx={{
          width: open ? 240 : 60,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: open ? 240 : 60,
            boxSizing: 'border-box',
            transition: 'width 0.3s ease',
            overflowX: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          },
        }}
      >
        <Box sx={{ padding: '8px 0', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: open ? 'row' : 'column' }}>
          <IconButton onClick={toggleDrawer} edge="start" sx={{ marginBottom: open ? '0px' : '8px' }}>
            <MenuIcon />
          </IconButton>
          {open && <Box sx={{ fontWeight: 'bold', fontSize: '1.2em', marginLeft: '10px' }}>{'{Logo} LearnAI'}</Box>}
        </Box>

        <List>
          <ListItem button sx={{ justifyContent: open ? 'flex-start' : 'center', paddingLeft: open ? '16px' : '8px' }}>
            <HomeIcon />
            {open && <ListItemText primary="Home" sx={{ marginLeft: '15px' }} />}
          </ListItem>
          <Divider />
          <ListItem button onClick={handleBookClick} sx={{ justifyContent: open ? 'flex-start' : 'center', paddingLeft: open ? '16px' : '8px' }}>
            <BookIcon />
            {open && <ListItemText primary="Book Name" sx={{ marginLeft: '15px' }} />}
            {open && (bookOpen ? <ExpandLess /> : <ExpandMore />)}
          </ListItem>
          <Collapse in={bookOpen && open} timeout="auto" unmountOnExit>
            <List component="div" disablePadding>
              <ListItem button sx={{ paddingLeft: open ? '30px' : '16px' }}>
                <ListItemText primary="Chapter Name" />
              </ListItem>
              <ListItem button sx={{ paddingLeft: open ? '45px' : '16px' }}>
                <ListItemText primary="SectionTitle" />
              </ListItem>
              <ListItem button sx={{ paddingLeft: open ? '45px' : '16px' }}>
                <ListItemText primary="Current Section" />
              </ListItem>
              <ListItem button sx={{ paddingLeft: open ? '45px' : '16px' }}>
                <ListItemText primary="SectionTitle" />
              </ListItem>
              <ListItem button sx={{ paddingLeft: open ? '30px' : '16px' }}>
                <ListItemText primary="Chapter Name" />
              </ListItem>
            </List>
          </Collapse>
        </List>

        <Box sx={{ bgcolor: '#4A90E2', marginTop: 'auto' }}>
          <List>
            <ListItem button sx={{ justifyContent: open ? 'flex-start' : 'center', paddingLeft: open ? '16px' : '8px' }}>
              <PersonIcon sx={{ color: '#FFFFFF' }} />
              {open && <ListItemText primary="Profile" sx={{ marginLeft: '15px', color: '#FFFFFF' }} />}
            </ListItem>
            <ListItem button sx={{ justifyContent: open ? 'flex-start' : 'center', paddingLeft: open ? '16px' : '8px' }}>
              <ExitToAppIcon sx={{ color: '#FFFFFF' }} />
              {open && <ListItemText primary="Logout" sx={{ marginLeft: '15px', color: '#FFFFFF' }} />}
            </ListItem>
          </List>
        </Box>
      </Drawer>
    </div>
  );
};

export default Sidebar;
