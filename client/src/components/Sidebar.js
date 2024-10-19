import React, { useState } from 'react';
import { Drawer, List, ListItem, ListItemText, IconButton, Divider, Collapse, Box, Typography } from '@mui/material';
import { Home as HomeIcon, MenuBook as BookIcon, Person as PersonIcon, ExitToApp as LogoutIcon, ExpandLess, ExpandMore } from '@mui/icons-material';
import MenuIcon from '@mui/icons-material/Menu';
import { Auth } from 'aws-amplify';
import { useNavigate } from 'react-router-dom';
import logo from '../static/logo.png';

const Sidebar = ({ onChapterSelect, onSectionSelect, setOpen, isOpen, bookStructure, bookTitle, file_id, filename, userId }) => {
  const [expandedChapter, setExpandedChapter] = useState(null);
  const navigate = useNavigate();

  const toggleDrawer = () => {
    setOpen(!isOpen);
  };

  const handleChapterClick = (chapterId) => {
    setExpandedChapter(expandedChapter === chapterId ? null : chapterId);
    onChapterSelect(chapterId);
  };

  const handleSectionClick = (sectionId) => {
    onSectionSelect(sectionId);
  };

  const handleLogout = async () => {
    try {
      await Auth.signOut();
      navigate('/');
    } catch (error) {
      console.error('Error signing out: ', error);
    }
  };

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: isOpen ? 240 : 60,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: isOpen ? 240 : 60,
          boxSizing: 'border-box',
          transition: 'width 0.3s ease',
          overflowX: 'hidden',
        },
      }}
      open={isOpen}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', padding: 2 }}>
        {isOpen && <img src={logo} alt="Logo" style={{ width: 40, height: 40, marginRight: 10 }} />}
        <IconButton onClick={toggleDrawer}>
          <MenuIcon />
        </IconButton>
      </Box>
      <Divider />
      <List>
        <ListItem button onClick={() => navigate('/')} sx={{ justifyContent: isOpen ? 'flex-start' : 'center' }}>
          <HomeIcon />
          {isOpen && <ListItemText primary="Home" sx={{ marginLeft: 2 }} />}
        </ListItem>
        <ListItem button onClick={() => navigate('/select-textbook')} sx={{ justifyContent: isOpen ? 'flex-start' : 'center' }}>
          <BookIcon />
          {isOpen && <ListItemText primary={bookTitle} sx={{ marginLeft: 2 }} />}
        </ListItem>
      </List>
      <Divider />
      <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
        <List>
          {bookStructure && bookStructure.chapters && bookStructure.chapters.map((chapter) => (
            <React.Fragment key={chapter.id}>
              <ListItem button onClick={() => handleChapterClick(chapter.id)}>
                <ListItemText primary={chapter.title} />
                {expandedChapter === chapter.id ? <ExpandLess /> : <ExpandMore />}
              </ListItem>
              <Collapse in={expandedChapter === chapter.id} timeout="auto" unmountOnExit>
                <List component="div" disablePadding>
                  {chapter.sections.map((section) => (
                    <ListItem 
                      button 
                      sx={{ pl: 4 }} 
                      key={section.id} 
                      onClick={() => handleSectionClick(section.id)}
                    >
                      <ListItemText primary={section.title} />
                    </ListItem>
                  ))}
                </List>
              </Collapse>
            </React.Fragment>
          ))}
        </List>
      </Box>
      <Divider />
      <List>
        <ListItem button sx={{ justifyContent: isOpen ? 'flex-start' : 'center' }}>
          <PersonIcon />
          {isOpen && <ListItemText primary="Profile" sx={{ marginLeft: 2 }} />}
        </ListItem>
        <ListItem button onClick={handleLogout} sx={{ justifyContent: isOpen ? 'flex-start' : 'center' }}>
          <LogoutIcon />
          {isOpen && <ListItemText primary="Logout" sx={{ marginLeft: 2 }} />}
        </ListItem>
      </List>
    </Drawer>
  );
};

export default Sidebar;
