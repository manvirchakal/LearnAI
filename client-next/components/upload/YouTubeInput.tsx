"use client";
import { Box, TextField, Typography, Alert } from "@mui/material";
import YouTubeIcon from "@mui/icons-material/YouTube";
import { useState } from "react";
import Button from "@/components/ui/Button";
import { useTranscribeYouTube } from "@/api/media";

export default function YouTubeInput() {
  const [url, setUrl] = useState("");
  const { mutate: transcribe, isPending, isSuccess, error, reset } = useTranscribeYouTube();

  const isValidYouTubeUrl = (s: string) =>
    /^https?:\/\/(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[\w-]+/.test(s);

  const handleSubmit = () => {
    if (!isValidYouTubeUrl(url)) return;
    transcribe({ url }, { onSuccess: () => setUrl("") });
  };

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
        <YouTubeIcon sx={{ color: "#ff0000" }} />
        <Typography fontWeight={600}>YouTube Video</Typography>
      </Box>

      <Box sx={{ display: "flex", gap: 1 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="https://youtube.com/watch?v=..."
          value={url}
          onChange={(e) => { setUrl(e.target.value); reset(); }}
          disabled={isPending}
        />
        <Button
          variant="contained"
          loading={isPending}
          disabled={!isValidYouTubeUrl(url)}
          onClick={handleSubmit}
        >
          Transcribe
        </Button>
      </Box>

      {isSuccess && (
        <Alert severity="success" sx={{ mt: 1.5 }}>
          Transcription started! Check the library when it finishes.
        </Alert>
      )}
      {error && (
        <Alert severity="error" sx={{ mt: 1.5 }}>
          Failed to start transcription.
        </Alert>
      )}
    </Box>
  );
}
