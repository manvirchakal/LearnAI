"use client";
import { AppBar, IconButton, Toolbar, Typography, Box } from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import { useUIStore } from "@/store/uiStore";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/upload", label: "Upload" },
  { href: "/library", label: "Library" },
  { href: "/collections", label: "Collections" },
  { href: "/media", label: "Media" },
  { href: "/questionnaire", label: "Profile" },
];

export default function TopNav({ showMenuButton = false }: { showMenuButton?: boolean }) {
  const { toggleSidebar } = useUIStore();
  const pathname = usePathname();

  return (
    <AppBar position="fixed" color="default" elevation={1} sx={{ bgcolor: "white", zIndex: 1300 }}>
      <Toolbar>
        {showMenuButton && (
          <IconButton edge="start" onClick={toggleSidebar} sx={{ mr: 2 }} aria-label="Toggle contents">
            <MenuIcon />
          </IconButton>
        )}
        <Link href="/home" style={{ textDecoration: "none" }}>
          <Typography variant="h6" sx={{ fontWeight: 700, color: "primary.main", cursor: "pointer" }}>
            LearnAI
          </Typography>
        </Link>
        <Box sx={{ flexGrow: 1 }} />
        <Box sx={{ display: "flex", gap: 2 }}>
          {NAV.map(({ href, label }) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link key={href} href={href} style={{ textDecoration: "none" }}>
                <Typography variant="body2" sx={{
                  color: active ? "primary.main" : "text.secondary",
                  fontWeight: active ? 600 : 400,
                  "&:hover": { color: "primary.main" },
                }}>
                  {label}
                </Typography>
              </Link>
            );
          })}
        </Box>
      </Toolbar>
    </AppBar>
  );
}
