"use client";
import { Alert, Box, LinearProgress, TextField, Typography } from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import InsertDriveFileIcon from "@mui/icons-material/InsertDriveFile";
import { useCallback, useState } from "react";
import Button from "@/components/ui/Button";
import { useUploadBook } from "@/api/books";
import { errorMessage } from "@/api/client";
import { useRouter } from "next/navigation";

export default function FileUploadZone() {
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [tocPages, setTocPages] = useState("");
  const router = useRouter();
  const { mutate: upload, isPending, error, isSuccess } = useUploadBook();
  const tocValid = tocPages === "" || /^\d+-\d+$/.test(tocPages);

  const handleFile = useCallback((f: File) => {
    if (f.type !== "application/pdf" && !f.name.toLowerCase().endsWith(".pdf")) return;
    setFile(f);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  };

  const handleUpload = () => {
    if (!file || !tocValid) return;
    upload(
      { file, tocPages: tocPages || undefined },
      { onSuccess: (book) => router.push(`/study/${book.file_id}`) },
    );
  };

  return (
    <Box sx={{ maxWidth: 520, mx: "auto" }}>
      <Box
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        component="label"
        htmlFor="pdf-upload-input"
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 1.5,
          p: 5,
          border: "2px dashed",
          borderColor: dragOver ? "primary.main" : "#dee2e6",
          borderRadius: 3,
          bgcolor: dragOver ? "primary.50" : "white",
          cursor: "pointer",
          transition: "all 0.15s",
          "&:hover": { borderColor: "primary.main", bgcolor: "#f0f7ff" },
        }}
      >
        <input
          id="pdf-upload-input"
          type="file"
          accept=".pdf"
          style={{ display: "none" }}
          onChange={handleChange}
        />

        {file ? (
          <>
            <InsertDriveFileIcon sx={{ fontSize: 48, color: "primary.main" }} />
            <Typography fontWeight={600}>{file.name}</Typography>
            <Typography variant="body2" color="text.secondary">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </Typography>
          </>
        ) : (
          <>
            <CloudUploadIcon sx={{ fontSize: 48, color: "text.disabled" }} />
            <Typography fontWeight={600} color="text.secondary">
              Drop your PDF here, or click to browse
            </Typography>
            <Typography variant="caption" color="text.disabled">PDF files only</Typography>
          </>
        )}
      </Box>

      {isPending && <LinearProgress sx={{ mt: 2, borderRadius: 1 }} />}
      {file && !isSuccess && (
        <TextField
          fullWidth
          size="small"
          sx={{ mt: 2 }}
          label="Table of contents pages (optional)"
          placeholder="e.g. 5-9"
          value={tocPages}
          onChange={(e) => setTocPages(e.target.value.trim())}
          error={!tocValid}
          helperText={
            tocValid
              ? "Only needed if the PDF has no built-in outline; the printed TOC on these pages is read by Claude."
              : "Use a page range like 5-9"
          }
        />
      )}
      {error && <Alert severity="error" sx={{ mt: 2 }}>Upload failed: {errorMessage(error)}</Alert>}
      {isSuccess && <Alert severity="success" sx={{ mt: 2 }}>Upload complete! Opening your book…</Alert>}

      {file && !isSuccess && (
        <Button
          fullWidth
          variant="contained"
          sx={{ mt: 2 }}
          loading={isPending}
          disabled={!tocValid}
          onClick={handleUpload}
        >
          Upload PDF
        </Button>
      )}
    </Box>
  );
}
