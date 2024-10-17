import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Drawer, List, ListItem, ListItemText, IconButton, Divider, Collapse, Box } from '@mui/material';
import { Home as HomeIcon, MenuBook as BookIcon, Person as PersonIcon, ExitToApp as LogoutIcon, ExpandLess, ExpandMore } from '@mui/icons-material';
import MenuIcon from '@mui/icons-material/Menu';
import { Auth } from 'aws-amplify';
import { useNavigate } from 'react-router-dom';
import logo from '../static/logo.png';

const Sidebar = ({ onChapterSelect, onSectionSelect, setOpen }) => {
  const [open, setOpenState] = useState(false);
  const [bookOpen, setBookOpen] = useState(false);
  const [chapters, setChapters] = useState([]);
  const [textbookTitle, setTextbookTitle] = useState('');
  const navigate = useNavigate();

  const toggleDrawer = () => {
    setOpenState(!open);
    setOpen(!open);
  };

  const handleBookClick = () => {
    setBookOpen(!bookOpen);
  };

  // Fetch textbook structure (chapters and sections) using Axios
  useEffect(() => {
    const fetchTextbookStructure = async () => {
      try {
        const response = await axios.get('http://localhost:8000/textbooks/1/structure/');
        const data = response.data;
        setTextbookTitle(data.textbook_title);
        setChapters(data.chapters);
      } catch (error) {
        console.error('Error fetching textbook structure:', error);
      }
    };

    fetchTextbookStructure();
  }, []);

  const handleLogout = async () => {
    try {
      await Auth.signOut();
      navigate('/');
    } catch (error) {
      console.error('Error signing out: ', error);
    }
  };

  return (
    <div>
      <Drawer
        variant="permanent"
        sx={{
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: open ? 240 : 60,
            boxSizing: 'border-box',
            transition: 'width 0.3s ease',
            overflowX: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          },
        }}
      >
        <Box sx={{ padding: '16px 0', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: open ? 'row' : 'column' }}>
          <IconButton onClick={toggleDrawer} edge="start" sx={{ marginBottom: open ? '0px' : '16px', padding: '12px' }}>
            <MenuIcon sx={{ fontSize: '32px' }} />
          </IconButton>
          {open && (
            <Box sx={{ marginLeft: '20px' }}>
              <img src={logo} alt="Logo" style={{ height: '50px', width: 'auto' }} />
            </Box>
          )}
        </Box>

        <List>
          <ListItem button onClick={() => navigate('/')} sx={{ justifyContent: open ? 'flex-start' : 'center', paddingLeft: open ? '16px' : '8px' }}>
            <HomeIcon />
            {open && <ListItemText primary="Home" sx={{ marginLeft: '15px' }} />}
          </ListItem>
          <Divider />
          <ListItem button onClick={handleBookClick} sx={{ justifyContent: open ? 'flex-start' : 'center', paddingLeft: open ? '16px' : '8px' }}>
            <BookIcon />
            {open && <ListItemText primary={textbookTitle || "Book Name"} sx={{ marginLeft: '15px' }} />}
            {open && (bookOpen ? <ExpandLess /> : <ExpandMore />)}
          </ListItem>
        </List>

        <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
          <Collapse in={bookOpen && open} timeout="auto" unmountOnExit>
            <List component="div" disablePadding>
              {chapters.map((chapter) => (
                <div key={chapter.id}>
                  <ListItem button sx={{ paddingLeft: open ? '30px' : '16px' }} onClick={() => onChapterSelect(chapter.id)}>
                    <ListItemText primary={chapter.title} />
                  </ListItem>
                  {chapter.sections.map((section) => (
                    <ListItem key={section.id} button sx={{ paddingLeft: open ? '45px' : '16px' }} onClick={() => onSectionSelect(section.id)}>
                      <ListItemText primary={section.title} />
                    </ListItem>
                  ))}
                </div>
              ))}
            </List>
          </Collapse>
        </Box>

        <Box sx={{ bgcolor: '#4A90E2', mt: 'auto' }}>
          <List>
            <ListItem button sx={{ justifyContent: open ? 'flex-start' : 'center', paddingLeft: open ? '16px' : '8px' }}>
              <PersonIcon sx={{ color: '#FFFFFF' }} />
              {open && <ListItemText primary="Profile" sx={{ marginLeft: '15px', color: '#FFFFFF' }} />}
            </ListItem>
            <ListItem button onClick={handleLogout} sx={{ justifyContent: open ? 'flex-start' : 'center', paddingLeft: open ? '16px' : '8px' }}>
              <LogoutIcon sx={{ color: '#FFFFFF' }} />
              {open && <ListItemText primary="Logout" sx={{ marginLeft: '15px', color: '#FFFFFF' }} />}
            </ListItem>
          </List>
        </Box>
      </Drawer>
    </div>
  );
};

export default Sidebar;
