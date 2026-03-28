"use client";
import { AppBar, IconButton, Toolbar, Typography, Box } from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import { useUIStore } from "@/store/uiStore";
import Link from "next/link";

export default function TopNav() {
  const { toggleSidebar } = useUIStore();

  return (
    <AppBar position="fixed" color="default" elevation={1} sx={{ bgcolor: "white", zIndex: 1300 }}>
      <Toolbar>
        <IconButton edge="start" onClick={toggleSidebar} sx={{ mr: 2 }}>
          <MenuIcon />
        </IconButton>
        <Link href="/home" style={{ textDecoration: "none" }}>
          <Typography variant="h6" sx={{ fontWeight: 700, color: "primary.main", cursor: "pointer" }}>
            LearnAI
          </Typography>
        </Link>
        <Box sx={{ flexGrow: 1 }} />
        <Box sx={{ display: "flex", gap: 2 }}>
          <Link href="/upload" style={{ textDecoration: "none" }}>
            <Typography variant="body2" sx={{ color: "text.secondary", cursor: "pointer", "&:hover": { color: "primary.main" } }}>
              Upload
            </Typography>
          </Link>
          <Link href="/library" style={{ textDecoration: "none" }}>
            <Typography variant="body2" sx={{ color: "text.secondary", cursor: "pointer", "&:hover": { color: "primary.main" } }}>
              Library
            </Typography>
          </Link>
        </Box>
      </Toolbar>
    </AppBar>
  );
}
