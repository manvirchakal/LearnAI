"use client";
import { Box, TextField, Typography, Alert } from "@mui/material";
import YouTubeIcon from "@mui/icons-material/YouTube";
import Link from "next/link";
import { useState } from "react";
import Button from "@/components/ui/Button";
import { errorMessage } from "@/api/client";
import { useTranscribeYouTube } from "@/api/media";

export default function YouTubeInput() {
  const [url, setUrl] = useState("");
  const { mutate: transcribe, data, isPending, isSuccess, error, reset } = useTranscribeYouTube();

  const isValidYouTubeUrl = (s: string) =>
    /^https?:\/\/(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[\w-]+/.test(s);

  const handleSubmit = () => {
    if (!isValidYouTubeUrl(url)) return;
    transcribe(url, { onSuccess: () => setUrl("") });
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
      {isPending && (
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
          Downloading and transcribing; long videos take a few minutes.
        </Typography>
      )}

      {isSuccess && (
        <Alert severity="success" sx={{ mt: 1.5 }}>
          Transcribed &ldquo;{data.title}&rdquo;. <Link href={`/media/transcriptions/${data.job_id}`}>View transcript</Link>
        </Alert>
      )}
      {error && (
        <Alert severity="error" sx={{ mt: 1.5 }}>
          Transcription failed: {errorMessage(error)}
        </Alert>
      )}
    </Box>
  );
}
