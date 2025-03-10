import React, { useState } from 'react';
import { Drawer, List, ListItem, ListItemIcon, ListItemText, IconButton, Box, Collapse } from '@mui/material';
import { Home as HomeIcon, MenuBook as BookIcon, Person as PersonIcon, ExitToApp as LogoutIcon, ExpandLess, ExpandMore, Menu as MenuIcon } from '@mui/icons-material';
import { Auth } from 'aws-amplify';
import { useNavigate } from 'react-router-dom';
import logo from '../static/logo.png';

const Sidebar = ({ onChapterSelect, onSectionSelect, setOpen, isOpen, bookStructure, bookTitle, currentSection }) => {
  const [expandedChapter, setExpandedChapter] = useState(null);
  const navigate = useNavigate();
  const collapsedWidth = 60; // Width of the collapsed sidebar

  const toggleDrawer = () => {
    setOpen(!isOpen);
  };

  const handleChapterClick = (chapterId) => {
    console.log("Handling chapter click:", chapterId);
    setExpandedChapter(expandedChapter === chapterId ? null : chapterId);
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
          bgcolor: 'background.paper',
          position: 'fixed',
          height: '100%',
          zIndex: 1200,
          borderRight: 'none',
        },
      }}
      open={isOpen}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', padding: 2, bgcolor: 'background.paper' }}>
        <IconButton onClick={toggleDrawer} sx={{ mr: 1 }}>
          <MenuIcon />
        </IconButton>
        <img src={logo} alt="LearnAI Logo" style={{ height: '40px' }} />
      </Box>
      <List>
        <ListItem button onClick={() => navigate('/')} sx={{ bgcolor: 'primary.main', color: 'white' }}>
          <ListItemIcon sx={{ color: 'white', minWidth: collapsedWidth }}>
            <HomeIcon />
          </ListItemIcon>
          {isOpen && <ListItemText primary="Home" />}
        </ListItem>
        <ListItem button onClick={() => navigate('/select-textbook')} sx={{ bgcolor: 'background.paper' }}>
          <ListItemIcon sx={{ minWidth: collapsedWidth }}>
            <BookIcon />
          </ListItemIcon>
          {isOpen && <ListItemText primary={bookTitle || "Book Name"} />}
        </ListItem>
      </List>
      <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
        <List>
          {bookStructure && bookStructure.chapters && bookStructure.chapters.map((chapter) => (
            <React.Fragment key={chapter.id}>
              <ListItem 
                button 
                onClick={() => handleChapterClick(chapter.id)} 
                sx={{ 
                  bgcolor: 'grey.100',
                  pl: `${collapsedWidth}px`,
                  display: isOpen ? 'flex' : 'none'
                }}
              >
                <ListItemText primary={chapter.title} />
                {chapter.sections && chapter.sections.length > 0 && (
                  expandedChapter === chapter.id ? <ExpandLess /> : <ExpandMore />
                )}
              </ListItem>
              <Collapse in={isOpen && expandedChapter === chapter.id} timeout="auto" unmountOnExit>
                <List component="div" disablePadding>
                  {chapter.sections.map((section) => (
                    <ListItem 
                      button 
                      sx={{ 
                        pl: `${collapsedWidth + 16}px`,
                        bgcolor: currentSection === section.id ? 'rgba(25, 118, 210, 0.15)' : 'background.paper', // Lower opacity blue
                        color: currentSection === section.id ? 'primary.main' : 'inherit', // Blue text for current section
                        '&:hover': {
                          bgcolor: currentSection === section.id ? 'rgba(25, 118, 210, 0.25)' : 'action.hover', // Slightly darker on hover
                        },
                      }} 
                      key={section.id} 
                      onClick={() => handleSectionClick(section.id)}
                    >
                      <ListItemText 
                        primary={section.title} 
                        primaryTypographyProps={{
                          style: {
                            fontWeight: currentSection === section.id ? 'bold' : 'normal',
                          }
                        }}
                      />
                    </ListItem>
                  ))}
                </List>
              </Collapse>
            </React.Fragment>
          ))}
        </List>
      </Box>
      <List sx={{ bgcolor: 'primary.main', color: 'white' }}>
        <ListItem button>
          <ListItemIcon sx={{ color: 'white', minWidth: collapsedWidth }}>
            <PersonIcon />
          </ListItemIcon>
          {isOpen && <ListItemText primary="Profile" />}
        </ListItem>
        <ListItem button onClick={handleLogout}>
          <ListItemIcon sx={{ color: 'white', minWidth: collapsedWidth }}>
            <LogoutIcon />
          </ListItemIcon>
          {isOpen && <ListItemText primary="Logout" />}
        </ListItem>
      </List>
    </Drawer>
  );
};

export default Sidebar;
