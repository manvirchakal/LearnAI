"use client";
import { Box, Typography, Grid } from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import LibraryBooksIcon from "@mui/icons-material/LibraryBooks";
import PsychologyIcon from "@mui/icons-material/Psychology";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import Card from "@/components/ui/Card";

const tiles = [
  {
    href: "/upload",
    icon: <CloudUploadIcon sx={{ fontSize: 40, color: "primary.main" }} />,
    title: "Upload Material",
    desc: "Add PDFs, YouTube lectures, or presentations.",
  },
  {
    href: "/library",
    icon: <LibraryBooksIcon sx={{ fontSize: 40, color: "primary.main" }} />,
    title: "My Library",
    desc: "Browse and study your uploaded textbooks.",
  },
  {
    href: "/questionnaire",
    icon: <PsychologyIcon sx={{ fontSize: 40, color: "primary.main" }} />,
    title: "Learning Profile",
    desc: "Discover your VARK learning style.",
  },
];

export default function HomePage() {
  return (
    <AppShell>
      <Box sx={{ p: 4 }}>
        <Typography variant="h4" fontWeight={700} gutterBottom>
          Welcome to LearnAI
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          Upload your study material and let AI tailor the experience to your learning style.
        </Typography>

        <Grid container spacing={3}>
          {tiles.map((tile) => (
            <Grid item xs={12} sm={6} md={4} key={tile.href}>
              <Link href={tile.href} style={{ textDecoration: "none" }}>
                <Card
                  sx={{
                    cursor: "pointer",
                    transition: "transform 0.15s, box-shadow 0.15s",
                    "&:hover": { transform: "translateY(-3px)", boxShadow: "0 6px 20px rgba(0,0,0,0.1)" },
                  }}
                >
                  <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", gap: 1.5 }}>
                    {tile.icon}
                    <Typography fontWeight={700} variant="h6">{tile.title}</Typography>
                    <Typography variant="body2" color="text.secondary">{tile.desc}</Typography>
                  </Box>
                </Card>
              </Link>
            </Grid>
          ))}
        </Grid>
      </Box>
    </AppShell>
  );
}
