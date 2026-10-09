"use client";
import { CalendarIcon, MessageSquareTextIcon, PresentationIcon } from "lucide-react";
import { use } from "react";
import MediaDetail from "@/components/media/MediaDetail";
import { Badge } from "@/components/ui/badge";
import { usePresentation } from "@/api/media";
import { formatDate } from "@/lib/materials";

export default function PresentationPage({ params }: { params: Promise<{ presentationId: string }> }) {
  const { presentationId } = use(params);
  const { data, isPending, error } = usePresentation(presentationId);
  const meta = data?.metadata;

  return (
    <MediaDetail
      tab="presentations"
      isPending={isPending}
      error={error}
      icon={PresentationIcon}
      eyebrow={
        meta && (
          <span className="inline-flex flex-wrap gap-1.5">
            <Badge variant="secondary" className="font-normal">{meta.total_slides} slides</Badge>
            {meta.has_speaker_notes && (
              <Badge variant="outline" className="font-normal">Speaker notes</Badge>
            )}
          </span>
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
      kind="presentations"
      item={meta && { presentation_id: meta.presentation_id, title: meta.original_filename }}
      collectionId={meta?.collection_id}
    >
      <ol className="flex flex-col gap-4">
        {data?.slides.map((slide, i) => {
          const body = slide.content.filter((c) => c !== slide.title);
          return (
            <li
              key={i}
              className="overflow-hidden rounded-xl border bg-card shadow-xs transition-shadow hover:shadow-sm"
            >
              <div className="flex items-start gap-3 p-5 sm:p-6">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-sm font-semibold text-primary tabular-nums ring-1 ring-primary/15">
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <h2 className="font-semibold break-words">
                    {slide.title || <span className="text-muted-foreground italic">Untitled slide</span>}
                  </h2>
                  {body.length > 0 && (
                    <div className="mt-2 space-y-1.5">
                      {body.map((text, j) => (
                        <p key={j} className="text-sm leading-6 break-words whitespace-pre-wrap text-card-foreground/85">
                          {text}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              {slide.notes && (
                <div className="border-t bg-muted/40 px-5 py-4 sm:px-6">
                  <p className="mb-1 inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                    <MessageSquareTextIcon className="size-3.5" />
                    Speaker notes
                  </p>
                  <p className="text-sm leading-6 break-words whitespace-pre-wrap text-muted-foreground">{slide.notes}</p>
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </MediaDetail>
  );
}
