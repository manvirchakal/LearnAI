"use client";
import { Alert, Box, Typography } from "@mui/material";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import Link from "next/link";
import { useRef, useState } from "react";
import Button from "@/components/ui/Button";
import { errorMessage } from "@/api/client";
import { useUploadNotes } from "@/api/media";

export default function NotesUpload() {
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { mutate: upload, data, isPending, isSuccess, error, reset } = useUploadNotes();

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
        <DescriptionOutlinedIcon color="success" />
        <Typography fontWeight={600}>Notes (PDF or image)</Typography>
      </Box>

      <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
        <Button variant="outlined" onClick={() => inputRef.current?.click()}>
          {file ? file.name : "Choose file"}
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          style={{ display: "none" }}
          onChange={(e) => { const f = e.target.files?.[0]; if (f) { setFile(f); reset(); } }}
        />
        {file && (
          <Button variant="contained" loading={isPending} onClick={() => upload(file, { onSuccess: () => setFile(null) })}>
            Upload
          </Button>
        )}
      </Box>

      {isSuccess && (
        <Alert severity="success" sx={{ mt: 1.5 }}>
          Notes saved. <Link href={`/media/notes/${data.notes_id}`}>View notes</Link>
        </Alert>
      )}
      {error && <Alert severity="error" sx={{ mt: 1.5 }}>Upload failed: {errorMessage(error)}</Alert>}
    </Box>
  );
}
