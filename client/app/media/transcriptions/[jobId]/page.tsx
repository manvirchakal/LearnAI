"use client";
import { Typography } from "@mui/material";
import MediaDetail from "@/components/media/MediaDetail";
import Card from "@/components/ui/Card";
import { useTranscription } from "@/api/media";
import { formatDate } from "@/lib/materials";

export default function TranscriptionPage({ params }: { params: { jobId: string } }) {
  const { data, isPending, error } = useTranscription(params.jobId);
  const meta = data?.metadata;

  return (
    <MediaDetail
      tab="transcriptions"
      isPending={isPending}
      error={error}
      title={meta?.title}
      subtitle={
        meta && (
          <>
            {meta.source_type === "youtube" ? "YouTube video" : "Recorded lecture"} · transcribed{" "}
            {formatDate(meta.transcription_date)}
            {meta.video_url && (
              <>
                {" · "}
                <a href={meta.video_url} target="_blank" rel="noopener noreferrer">Watch</a>
              </>
            )}
          </>
        )
      }
      kind="transcriptions"
      item={meta && { transcription_id: meta.job_id, title: meta.title }}
      collectionId={meta?.collection_id}
    >
      <Card>
        <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", lineHeight: 1.8 }}>{data?.transcript}</Typography>
      </Card>
    </MediaDetail>
  );
}
