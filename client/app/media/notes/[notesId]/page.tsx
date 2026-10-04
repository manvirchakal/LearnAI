"use client";
import { Typography } from "@mui/material";
import MediaDetail from "@/components/media/MediaDetail";
import Card from "@/components/ui/Card";
import { useNotes } from "@/api/media";
import { formatDate } from "@/lib/materials";

export default function NotesPage({ params }: { params: { notesId: string } }) {
  const { data, isPending, error } = useNotes(params.notesId);
  const meta = data?.metadata;
  const blocks = data?.content.text_content ?? [];

  return (
    <MediaDetail
      tab="notes"
      isPending={isPending}
      error={error}
      title={meta?.original_filename}
      subtitle={meta && `Uploaded ${formatDate(meta.upload_date)}`}
      kind="notes"
      item={meta && { notes_id: meta.notes_id, title: meta.original_filename }}
      collectionId={meta?.collection_id}
    >
      <Card>
        {blocks.length ? blocks.map((b, i) => (
          <Typography key={i} variant="body2" sx={{ whiteSpace: "pre-wrap", mb: 1.5 }}>{b.text}</Typography>
        )) : (
          <Typography variant="body2" color="text.secondary">No text could be extracted from these notes.</Typography>
        )}
      </Card>
    </MediaDetail>
  );
}
