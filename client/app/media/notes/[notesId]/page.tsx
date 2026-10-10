"use client";
import { CalendarIcon, FileTextIcon, FileXIcon } from "lucide-react";
import { use } from "react";
import MediaDetail from "@/components/media/MediaDetail";
import { EmptyState } from "@/components/shared/States";
import { Badge } from "@/components/ui/badge";
import { useNotes } from "@/api/media";
import { formatDate } from "@/lib/materials";

export default function NotesPage({ params }: { params: Promise<{ notesId: string }> }) {
  const { notesId } = use(params);
  const { data, isPending, error } = useNotes(notesId);
  const meta = data?.metadata;
  const blocks = data?.content.text_content ?? [];

  return (
    <MediaDetail
      tab="notes"
      isPending={isPending}
      error={error}
      icon={FileTextIcon}
      eyebrow={
        meta?.file_type && (
          <Badge variant="secondary" className="font-normal">
            {meta.file_type.replace(/^\./, "").toUpperCase()}
          </Badge>
        )
      }
      title={meta?.original_filename}
      subtitle={
        meta && (
          <span className="inline-flex items-center gap-1">
            <CalendarIcon className="size-3.5" />
            Uploaded {formatDate(meta.upload_date)}
          </span>
        )
      }
      kind="notes"
      item={meta && { notes_id: meta.notes_id, title: meta.original_filename }}
      collectionId={meta?.collection_id}
    >
      {blocks.length ? (
        <article className="space-y-4 rounded-xl border bg-card p-5 shadow-xs sm:p-8">
          {blocks.map((b, i) => (
            <p key={i} className="text-[15px] leading-7 break-words whitespace-pre-wrap text-card-foreground/90">
              {b.text}
            </p>
          ))}
        </article>
      ) : (
        <EmptyState
          icon={FileXIcon}
          title="No text found"
          description="No text could be extracted from these notes."
          className="rounded-xl border border-dashed bg-card/50"
        />
      )}
    </MediaDetail>
  );
}
