"use client";
import { Box, Typography, Divider } from "@mui/material";
import AppShell from "@/components/layout/AppShell";
import FileUploadZone from "@/components/upload/FileUploadZone";
import YouTubeInput from "@/components/upload/YouTubeInput";
import LectureRecorder from "@/components/upload/LectureRecorder";
import PresentationUpload from "@/components/upload/PresentationUpload";
import Card from "@/components/ui/Card";

export default function UploadPage() {
  return (
    <AppShell>
      <Box sx={{ p: 4, maxWidth: 720, mx: "auto" }}>
        <Typography variant="h5" fontWeight={700} gutterBottom>Upload Material</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          Add textbooks, lectures, or presentations to your library.
        </Typography>

        <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
          <Card>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>PDF Textbook</Typography>
            <Divider sx={{ mb: 2 }} />
            <FileUploadZone />
          </Card>

          <Card>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>Online Sources</Typography>
            <Divider sx={{ mb: 2 }} />
            <YouTubeInput />
          </Card>

          <Card>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>Record a Lecture</Typography>
            <Divider sx={{ mb: 2 }} />
            <LectureRecorder />
          </Card>

          <Card>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>Presentation Slides</Typography>
            <Divider sx={{ mb: 2 }} />
            <PresentationUpload />
          </Card>
        </Box>
      </Box>
    </AppShell>
  );
}
