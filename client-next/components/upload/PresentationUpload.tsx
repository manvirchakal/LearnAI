"use client";
import { Box, Typography, Alert } from "@mui/material";
import SlideshowIcon from "@mui/icons-material/Slideshow";
import { useRef, useState } from "react";
import Button from "@/components/ui/Button";
import { useProcessPresentation } from "@/api/media";

export default function PresentationUpload() {
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { mutate: upload, isPending, isSuccess, error, reset } = useProcessPresentation();

  const handleFile = (f: File) => {
    if (!f.name.match(/\.(pptx?|odp)$/i)) return;
    setFile(f);
    reset();
  };

  const handleUpload = () => {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    upload(formData, { onSuccess: () => setFile(null) });
  };

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
        <SlideshowIcon color="primary" />
        <Typography fontWeight={600}>PowerPoint / Presentation</Typography>
      </Box>

      <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
        <Button variant="outlined" onClick={() => inputRef.current?.click()}>
          {file ? file.name : "Choose .pptx file"}
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept=".ppt,.pptx,.odp"
          style={{ display: "none" }}
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />
        {file && (
          <Button variant="contained" loading={isPending} onClick={handleUpload}>
            Process
          </Button>
        )}
      </Box>

      {isSuccess && <Alert severity="success" sx={{ mt: 1.5 }}>Presentation processed and saved!</Alert>}
      {error && <Alert severity="error" sx={{ mt: 1.5 }}>Failed to process presentation.</Alert>}
    </Box>
  );
}
