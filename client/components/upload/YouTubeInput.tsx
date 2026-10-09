"use client";
import { LinkIcon, WandSparklesIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ErrorAlert } from "@/components/shared/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { errorMessage } from "@/api/client";
import { useTranscribeYouTube } from "@/api/media";
import SuccessAlert from "./ResultAlert";

export default function YouTubeInput() {
  const [url, setUrl] = useState("");
  const { mutate: transcribe, data, isPending, isSuccess, error, reset } = useTranscribeYouTube();

  const isValidYouTubeUrl = (s: string) =>
    /^https?:\/\/(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[\w-]+/.test(s);

  const handleSubmit = () => {
    if (!isValidYouTubeUrl(url)) return;
    transcribe(url, {
      onSuccess: (res) => {
        setUrl("");
        toast.success(`Transcribed “${res.title}”`);
      },
    });
  };

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
            onChange={(e) => { setUrl(e.target.value); reset(); }}
            disabled={isPending}
            aria-label="YouTube URL"
          />
        </div>
        <Button type="submit" disabled={!isValidYouTubeUrl(url) || isPending}>
          {isPending ? <Spinner /> : <WandSparklesIcon />}
          Transcribe
        </Button>
      </form>
      {isPending && (
        <p className="text-xs text-muted-foreground">
          Downloading and transcribing; long videos take a few minutes.
        </p>
      )}

      {isSuccess && (
        <SuccessAlert href={`/media/transcriptions/${data.job_id}`} linkLabel="View transcript">
          Transcribed &ldquo;{data.title}&rdquo;.
        </SuccessAlert>
      )}
      {error && <ErrorAlert title="Transcription failed">{errorMessage(error)}</ErrorAlert>}
    </div>
  );
}
