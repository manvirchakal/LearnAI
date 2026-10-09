"use client";
import { InboxIcon } from "lucide-react";
import { useState, type JSX } from "react";
import { toast } from "sonner";
import { KindIcon } from "@/components/collections/MaterialList";
import { ErrorAlert } from "@/components/shared/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useBook, useBooks } from "@/api/books";
import { errorMessage } from "@/api/client";
import { useUpdateCollectionMaterials } from "@/api/collections";
import { useNotesList, usePresentations, useTranscriptions } from "@/api/media";
import { formatDate, hasMaterial, KIND_LABELS, withMaterial, withoutMaterial, type MaterialRef } from "@/lib/materials";
import { cn } from "@/lib/utils";
import { MATERIAL_KINDS, materialCount, type Collection, type CollectionMaterials, type MaterialKind } from "@/types/collection";

interface Option {
  ref: MaterialRef;
  primary: string;
  secondary?: string;
}

interface ToggleProps {
  kind: MaterialKind;
  draft: CollectionMaterials;
  onToggle: (kind: MaterialKind, ref: MaterialRef) => void;
}

function ListSkeleton() {
  return (
    <div className="flex flex-col gap-2 p-1">
      {[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-11 w-full rounded-lg" />)}
    </div>
  );
}

function EmptyPane({ children }: { children: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center text-sm text-muted-foreground">
      <InboxIcon className="size-6 opacity-60" />
      {children}
    </div>
  );
}

function OptionList({ kind, options, draft, onToggle, empty }: ToggleProps & { options: Option[]; empty: string }) {
  if (!options.length) return empty ? <EmptyPane>{empty}</EmptyPane> : null;
  return (
    <ul className="flex flex-col gap-0.5">
      {options.map((o) => {
        const checked = hasMaterial(draft, kind, o.ref);
        const id = `pick-${kind}-${JSON.stringify(o.ref)}`;
        return (
          <li key={o.primary + (o.secondary ?? "") + JSON.stringify(o.ref)}>
            <label
              htmlFor={id}
              className={cn(
                "flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-accent/60",
                checked && "bg-primary/5 hover:bg-primary/10",
              )}
            >
              <Checkbox id={id} checked={checked} onCheckedChange={() => onToggle(kind, o.ref)} aria-label={o.primary} />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm">{o.primary}</span>
                {o.secondary && <span className="block truncate text-xs text-muted-foreground">{o.secondary}</span>}
              </span>
            </label>
          </li>
        );
      })}
    </ul>
  );
}

function BookSections(props: ToggleProps) {
  const books = useBooks();
  const [picked, setFileId] = useState("");
  // default to the first book until the user picks one
  const fileId = picked || books.data?.[0]?.file_id || "";
  const book = useBook(fileId);

  if (books.isPending) return <ListSkeleton />;
  if (!books.data?.length) return <EmptyPane>Upload a textbook first.</EmptyPane>;

  return (
    <div className="flex flex-col gap-3">
      <Select value={fileId} onValueChange={setFileId}>
        <SelectTrigger className="w-full" aria-label="Book">
          <SelectValue placeholder="Choose a book" />
        </SelectTrigger>
        <SelectContent>
          {books.data.map((b) => <SelectItem key={b.file_id} value={b.file_id}>{b.title}</SelectItem>)}
        </SelectContent>
      </Select>
      {book.isPending && fileId ? <ListSkeleton /> : book.data?.chapters.map((chapter) => (
        <section key={chapter.id} className="flex flex-col gap-1">
          <h4 className="px-3 pt-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">
            {chapter.number} {chapter.title}
          </h4>
          <OptionList
            {...props}
            empty=""
            options={chapter.sections.map((s) => ({
              ref: { file_id: book.data.file_id, section_id: s.id, title: `${book.data.title}: ${s.title}` },
              primary: s.title,
              secondary: `pp. ${s.start_page}–${s.end_page}`,
            }))}
          />
        </section>
      ))}
    </div>
  );
}

function Transcriptions(props: ToggleProps) {
  const { data, isPending } = useTranscriptions();
  if (isPending) return <ListSkeleton />;
  return (
    <OptionList {...props} empty="No transcribed lectures or videos yet."
      options={(data ?? []).map((t) => ({
        ref: { transcription_id: t.job_id, title: t.title },
        primary: t.title,
        secondary: `${t.source_type === "youtube" ? "YouTube" : "Lecture"} · ${formatDate(t.transcription_date)}`,
      }))} />
  );
}

function Presentations(props: ToggleProps) {
  const { data, isPending } = usePresentations();
  if (isPending) return <ListSkeleton />;
  return (
    <OptionList {...props} empty="No slide decks yet."
      options={(data ?? []).map((p) => ({
        ref: { presentation_id: p.presentation_id, title: p.original_filename },
        primary: p.original_filename,
        secondary: `${p.total_slides} slides · ${formatDate(p.upload_date)}`,
      }))} />
  );
}

function Notes(props: ToggleProps) {
  const { data, isPending } = useNotesList();
  if (isPending) return <ListSkeleton />;
  return (
    <OptionList {...props} empty="No notes yet."
      options={(data ?? []).map((n) => ({
        ref: { notes_id: n.notes_id, title: n.original_filename },
        primary: n.original_filename,
        secondary: formatDate(n.upload_date),
      }))} />
  );
}

const PANES: Record<MaterialKind, (p: ToggleProps) => JSX.Element | null> = {
  textbook_sections: BookSections,
  transcriptions: Transcriptions,
  presentations: Presentations,
  notes: Notes,
};

/** Choose a collection's materials from everything the user has uploaded. */
export default function MaterialPicker({ collection, open, onClose }: {
  collection: Collection;
  open: boolean;
  onClose: () => void;
}) {
  const [kind, setKind] = useState<MaterialKind>("textbook_sections");
  const [draft, setDraft] = useState(collection.materials);
  const update = useUpdateCollectionMaterials();

  // reset the draft whenever the dialog opens or the saved materials change
  const [synced, setSynced] = useState({ open, materials: collection.materials });
  if (synced.open !== open || synced.materials !== collection.materials) {
    setSynced({ open, materials: collection.materials });
    if (open) setDraft(collection.materials);
  }

  const toggle = (k: MaterialKind, ref: MaterialRef) =>
    setDraft((d) => (hasMaterial(d, k, ref) ? withoutMaterial(d, k, ref) : withMaterial(d, k, ref)));

  const Pane = PANES[kind];
  const save = () =>
    update.mutate(
      { collectionId: collection.collection_id, materials: draft },
      {
        onSuccess: () => {
          toast.success("Materials updated");
          onClose();
        },
      },
    );
  const selected = materialCount(draft);

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="flex max-h-[calc(100svh-2rem)] flex-col gap-4 sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Choose materials</DialogTitle>
          <DialogDescription>Select what to study together in &ldquo;{collection.name}&rdquo;.</DialogDescription>
        </DialogHeader>

        {update.error && <ErrorAlert>{errorMessage(update.error)}</ErrorAlert>}

        <Tabs value={kind} onValueChange={(v) => setKind(v as MaterialKind)} className="min-h-0 gap-3">
          <div className="-mx-6 overflow-x-auto border-b px-6">
            <TabsList variant="line" className="h-10 w-max">
              {MATERIAL_KINDS.map((k) => (
                <TabsTrigger key={k} value={k} className="gap-2 px-3">
                  <KindIcon kind={k} className="size-5 rounded [&_svg]:size-3" />
                  {KIND_LABELS[k].many}
                  {draft[k].length > 0 && (
                    <Badge variant="secondary" className="h-5 min-w-5 px-1.5 tabular-nums">{draft[k].length}</Badge>
                  )}
                </TabsTrigger>
              ))}
            </TabsList>
          </div>
          <div className="h-[360px] max-h-[50svh] overflow-y-auto">
            <Pane kind={kind} draft={draft} onToggle={toggle} />
          </div>
        </Tabs>

        <DialogFooter className="sm:items-center sm:justify-between">
          <p className="text-xs text-muted-foreground">
            <span className="font-medium text-foreground tabular-nums">{selected}</span> selected · changing materials
            regenerates the study guide
          </p>
          <div className="flex flex-col-reverse gap-2 sm:flex-row">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={save} disabled={update.isPending}>
              {update.isPending && <Spinner />}
              Save
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
