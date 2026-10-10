"use client";
import { LinkIcon, WandSparklesIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ErrorAlert } from "@/components/shared/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import { errorMessage } from "@/api/client";
import { useTranscribeYouTube, useTranscriptionTask } from "@/api/media";
import type { TranscriptionTask } from "@/types/media";
import SuccessAlert from "./ResultAlert";

const STAGE_LABELS: Record<TranscriptionTask["stage"], string> = {
  queued: "Waiting for another transcription to finish…",
  downloading: "Downloading audio…",
  transcribing: "Transcribing…",
  saving: "Saving transcript…",
  indexing: "Preparing it for study…",
  done: "Done",
};

export default function YouTubeInput() {
  const [url, setUrl] = useState("");
  const start = useTranscribeYouTube();
  const { data: task, error: pollError } = useTranscriptionTask(start.data?.task_id, (done) => {
    setUrl("");
    toast.success(`Transcribed “${done.title}”`);
  });

  const running = start.isPending || (!!start.data && !pollError && task?.status !== "done" && task?.status !== "failed");
  const result = task?.status === "done" ? task.result : null;
  const error = start.error ?? pollError ?? (task?.status === "failed" ? new Error(task.error ?? "Unknown error") : null);

  const isValidYouTubeUrl = (s: string) =>
    /^https?:\/\/(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[\w-]+/.test(s);

  const handleSubmit = () => {
    if (isValidYouTubeUrl(url)) start.mutate(url);
  };

  const stage = task?.stage ?? "queued";
  return (
    <div className="flex flex-col gap-3">
      <form
        className="flex flex-col gap-2 sm:flex-row"
        onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
      >
        <div className="relative flex-1">
          <LinkIcon className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="https://youtube.com/watch?v=..."
            value={url}
            onChange={(e) => { setUrl(e.target.value); if (!running) start.reset(); }}
            disabled={running}
            aria-label="YouTube URL"
          />
        </div>
        <Button type="submit" disabled={!isValidYouTubeUrl(url) || running}>
          {running ? <Spinner /> : <WandSparklesIcon />}
          Transcribe
        </Button>
      </form>

      {running && (
        <div className="flex flex-col gap-1.5" aria-live="polite">
          <div className="flex items-baseline justify-between gap-2 text-xs text-muted-foreground">
            <span className="min-w-0 truncate">
              {STAGE_LABELS[stage]}
              {task?.title && <> &ldquo;{task.title}&rdquo;</>}
            </span>
            {task?.progress != null && <span className="tabular-nums">{Math.round(task.progress * 100)}%</span>}
          </div>
          {/* An unknown amount done shows as an empty bar */}
          <Progress value={(task?.progress ?? 0) * 100} aria-label={STAGE_LABELS[stage]} />
        </div>
      )}

      {result && (
        <SuccessAlert href={`/media/transcriptions/${result.job_id}`} linkLabel="View transcript">
          Transcribed &ldquo;{result.title}&rdquo;.
        </SuccessAlert>
      )}
      {error && <ErrorAlert title="Transcription failed">{errorMessage(error)}</ErrorAlert>}
    </div>
  );
}
