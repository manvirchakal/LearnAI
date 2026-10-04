"use client";
import { Alert, Box, LinearProgress, TextField, Typography } from "@mui/material";
import MicIcon from "@mui/icons-material/Mic";
import StopIcon from "@mui/icons-material/Stop";
import { useRef, useState } from "react";
import Button from "@/components/ui/Button";
import { errorMessage } from "@/api/client";
import { useTranscribeLecture } from "@/api/media";

type RecordingState = "idle" | "recording" | "processing";

export default function LectureRecorder() {
  const [state, setState] = useState<RecordingState>("idle");
  const [seconds, setSeconds] = useState(0);
  const [title, setTitle] = useState("");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const { mutate: transcribe, isSuccess, error } = useTranscribeLecture();

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];

      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        const ext = blob.type.includes("ogg") ? "ogg" : blob.type.includes("mp4") ? "m4a" : "webm";
        setState("processing");
        transcribe(
          { audio: blob, filename: `lecture.${ext}`, title: title.trim() || `Lecture ${new Date().toLocaleString()}` },
          { onSettled: () => setState("idle") },
        );
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setState("recording");
      setSeconds(0);
      timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    } catch {
      alert("Microphone access denied.");
    }
  };

  const stopRecording = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    mediaRecorderRef.current?.stop();
  };

  const fmt = (s: number) => `${Math.floor(s / 60).toString().padStart(2, "0")}:${(s % 60).toString().padStart(2, "0")}`;

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
        <MicIcon color="error" />
        <Typography fontWeight={600}>Record Lecture</Typography>
      </Box>

      <TextField
        fullWidth
        size="small"
        label="Lecture title"
        placeholder="e.g. Week 3 — Thermodynamics"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        disabled={state !== "idle"}
        sx={{ mb: 2 }}
      />

      <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
        {state === "idle" && (
          <Button variant="contained" color="error" startIcon={<MicIcon />} onClick={startRecording}>
            Start Recording
          </Button>
        )}
        {state === "recording" && (
          <>
            <Button variant="outlined" color="error" startIcon={<StopIcon />} onClick={stopRecording}>
              Stop
            </Button>
            <Typography variant="body2" fontFamily="monospace" color="error.main">
              ● {fmt(seconds)}
            </Typography>
          </>
        )}
        {state === "processing" && (
          <Box sx={{ flex: 1 }}>
            <Typography variant="body2" gutterBottom>Transcribing…</Typography>
            <LinearProgress />
          </Box>
        )}
      </Box>

      {isSuccess && <Alert severity="success" sx={{ mt: 2 }}>Transcript saved — it&apos;s available as a collection for study.</Alert>}
      {error && <Alert severity="error" sx={{ mt: 2 }}>Transcription failed: {errorMessage(error)}</Alert>}
    </Box>
  );
}
