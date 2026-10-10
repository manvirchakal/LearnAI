"use client";
import { CalendarIcon, ExternalLinkIcon, MicIcon, MonitorPlayIcon } from "lucide-react";
import { use } from "react";
import MediaDetail from "@/components/media/MediaDetail";
import { Badge } from "@/components/ui/badge";
import { useTranscription } from "@/api/media";
import { formatDate } from "@/lib/materials";

export default function TranscriptionPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
  const { data, isPending, error } = useTranscription(jobId);
  const meta = data?.metadata;
  const youtube = meta?.source_type === "youtube";
  const transcript = data?.transcript?.trim() ?? "";
  const words = transcript ? transcript.split(/\s+/).length : 0;

  return (
    <MediaDetail
      tab="transcriptions"
      isPending={isPending}
      error={error}
      icon={youtube ? MonitorPlayIcon : MicIcon}
      eyebrow={
        meta && (
          <Badge variant="secondary" className="font-normal">
            {youtube ? "YouTube video" : "Recorded lecture"}
          </Badge>
        )
      }
      title={meta?.title}
      subtitle={
        meta && (
          <span className="inline-flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="inline-flex items-center gap-1">
              <CalendarIcon className="size-3.5" />
              Transcribed {formatDate(meta.transcription_date)}
            </span>
            {words > 0 && <span>{words.toLocaleString()} words</span>}
            {meta.video_url && (
              <a
                href={meta.video_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 font-medium text-primary underline-offset-4 hover:underline"
              >
                Watch
                <ExternalLinkIcon className="size-3.5" />
              </a>
            )}
          </span>
        )
      }
      kind="transcriptions"
      item={meta && { transcription_id: meta.job_id, title: meta.title }}
      collectionId={meta?.collection_id}
    >
      <article className="rounded-xl border bg-card p-5 shadow-xs sm:p-8">
        <h2 className="mb-4 text-xs font-medium tracking-wide text-muted-foreground uppercase">Transcript</h2>
        {transcript ? (
          <p className="text-[15px] leading-7 break-words whitespace-pre-wrap text-card-foreground/90">{transcript}</p>
        ) : (
          <p className="text-sm text-muted-foreground">No transcript text is available for this item.</p>
        )}
      </article>
    </MediaDetail>
  );
}
