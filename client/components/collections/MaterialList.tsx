"use client";
import { BookOpenIcon, FileTextIcon, ListPlusIcon, PresentationIcon, VideoIcon, XIcon, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { ErrorAlert } from "@/components/shared/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { errorMessage } from "@/api/client";
import { useUpdateCollectionMaterials } from "@/api/collections";
import { KIND_LABELS, materialHref, materialId, withoutMaterial, type MaterialRef } from "@/lib/materials";
import { cn } from "@/lib/utils";
import { MATERIAL_KINDS, type Collection, type MaterialKind } from "@/types/collection";

/** Icon and accent colour for each material kind. */
export const KIND_ICONS: Record<MaterialKind, LucideIcon> = {
  textbook_sections: BookOpenIcon,
  transcriptions: VideoIcon,
  presentations: PresentationIcon,
  notes: FileTextIcon,
};

export const KIND_TONES: Record<MaterialKind, string> = {
  textbook_sections: "bg-chart-1/10 text-chart-1 ring-chart-1/20",
  transcriptions: "bg-chart-2/10 text-chart-2 ring-chart-2/20",
  presentations: "bg-chart-3/10 text-chart-3 ring-chart-3/20",
  notes: "bg-chart-4/10 text-chart-4 ring-chart-4/20",
};

/** Small tinted square holding a kind's icon. */
export function KindIcon({ kind, className }: { kind: MaterialKind; className?: string }) {
  const Icon = KIND_ICONS[kind];
  return (
    <span className={cn("flex size-7 shrink-0 items-center justify-center rounded-md ring-1", KIND_TONES[kind], className)}>
      <Icon className="size-3.5" />
    </span>
  );
}

function label(kind: MaterialKind, ref: MaterialRef): string {
  const r = ref as unknown as Record<string, string | undefined>;
  return r.title || (kind === "textbook_sections" ? `Section ${r.section_id}` : `${KIND_LABELS[kind].one} ${materialId(kind, ref).slice(0, 8)}`);
}

/** A collection's materials, grouped by kind, each removable. */
export default function MaterialList({ collection, onEdit }: { collection: Collection; onEdit: () => void }) {
  const update = useUpdateCollectionMaterials();

  const remove = (kind: MaterialKind, ref: MaterialRef) =>
    update.mutate(
      { collectionId: collection.collection_id, materials: withoutMaterial(collection.materials, kind, ref) },
      { onSuccess: () => toast.success(`Removed “${label(kind, ref)}”`) },
    );

  const kinds = MATERIAL_KINDS.filter((k) => collection.materials[k].length);

  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">In this collection</p>
        <Button size="sm" variant="outline" onClick={onEdit}>
          <ListPlusIcon />
          Choose materials
        </Button>
      </div>
      {update.error && <ErrorAlert>{errorMessage(update.error)}</ErrorAlert>}
      {!kinds.length && (
        <div className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
          Nothing here yet.
        </div>
      )}
      {kinds.map((kind) => (
        <section key={kind} className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2 px-1">
            <h3 className="text-sm font-medium">{KIND_LABELS[kind].many}</h3>
            <Badge variant="secondary" className="tabular-nums">{collection.materials[kind].length}</Badge>
          </div>
          <ul className="divide-y overflow-hidden rounded-xl border bg-card shadow-xs">
            {(collection.materials[kind] as MaterialRef[]).map((ref) => {
              const text = label(kind, ref);
              return (
                <li key={materialId(kind, ref)} className="group flex items-center gap-3 px-3 py-2 transition-colors hover:bg-accent/50">
                  <KindIcon kind={kind} />
                  <Link
                    href={materialHref(kind, ref)}
                    title={text}
                    className="min-w-0 flex-1 truncate text-sm underline-offset-4 hover:underline"
                  >
                    {text}
                  </Link>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        className="text-muted-foreground opacity-100 hover:text-destructive sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100"
                        onClick={() => remove(kind, ref)}
                        disabled={update.isPending}
                        aria-label={`Remove ${text}`}
                      >
                        <XIcon />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Remove from collection</TooltipContent>
                  </Tooltip>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
