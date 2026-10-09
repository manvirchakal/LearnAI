"use client";
import { MicIcon, SquareIcon } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { ErrorAlert } from "@/components/shared/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { errorMessage } from "@/api/client";
import { useTranscribeLecture } from "@/api/media";
import SuccessAlert from "./ResultAlert";

type RecordingState = "idle" | "recording" | "processing";

export default function LectureRecorder() {
  const [state, setState] = useState<RecordingState>("idle");
  const [seconds, setSeconds] = useState(0);
  const [title, setTitle] = useState("");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const { mutate: transcribe, data, isSuccess, error } = useTranscribeLecture();

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
          {
            onSuccess: () => toast.success("Lecture transcript saved"),
            onSettled: () => setState("idle"),
          },
        );
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setState("recording");
      setSeconds(0);
      timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    } catch {
      toast.error("Microphone access denied.");
    }
  };

  const stopRecording = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    mediaRecorderRef.current?.stop();
  };

  const fmt = (s: number) => `${Math.floor(s / 60).toString().padStart(2, "0")}:${(s % 60).toString().padStart(2, "0")}`;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-2">
        <Label htmlFor="lecture-title">Lecture title</Label>
        <Input
          id="lecture-title"
          placeholder="e.g. Week 3 — Thermodynamics"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          disabled={state !== "idle"}
        />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {state === "idle" && (
          <Button variant="destructive" onClick={startRecording}>
            <MicIcon />
            Start Recording
          </Button>
        )}
        {state === "recording" && (
          <>
            <Button
              variant="outline"
              className="border-destructive/40 text-destructive hover:bg-destructive/10 hover:text-destructive"
              onClick={stopRecording}
            >
              <SquareIcon className="fill-current" />
              Stop
            </Button>
            <span className="inline-flex items-center gap-2 rounded-full bg-destructive/10 px-3 py-1 font-mono text-sm text-destructive tabular-nums">
              <span className="relative flex size-2">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-destructive opacity-75" />
                <span className="relative inline-flex size-2 rounded-full bg-destructive" />
              </span>
              REC {fmt(seconds)}
            </span>
          </>
        )}
        {state === "processing" && (
          <div className="flex items-center gap-2 rounded-lg border bg-muted/40 px-3 py-2 text-sm text-muted-foreground">
            <Spinner className="text-primary" />
            Transcribing…
          </div>
        )}
      </div>

      {isSuccess && (
        <SuccessAlert href={`/media/transcriptions/${data.job_id}`} linkLabel="View transcript">
          Transcript saved.
        </SuccessAlert>
      )}
      {error && <ErrorAlert title="Transcription failed">{errorMessage(error)}</ErrorAlert>}
    </div>
  );
}
