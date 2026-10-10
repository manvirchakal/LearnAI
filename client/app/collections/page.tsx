"use client";
import { ArrowUpRightIcon, CalendarIcon, FolderOpenIcon, LibraryIcon, PlusIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { KIND_ICONS, KIND_TONES } from "@/components/collections/MaterialList";
import AppShell from "@/components/layout/AppShell";
import PageHeader, { PageContainer } from "@/components/shared/PageHeader";
import { EmptyState, ErrorAlert } from "@/components/shared/States";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { errorMessage } from "@/api/client";
import { useCollections, useCreateCollection } from "@/api/collections";
import { formatDate, KIND_LABELS } from "@/lib/materials";
import { cn } from "@/lib/utils";
import { emptyMaterials, MATERIAL_KINDS, materialCount, type Collection } from "@/types/collection";

function CollectionCard({ collection }: { collection: Collection }) {
  const count = materialCount(collection.materials);
  const kinds = MATERIAL_KINDS.filter((k) => collection.materials[k].length);
  return (
    <Link
      href={`/collections/${collection.collection_id}`}
      className="group flex h-full flex-col gap-4 rounded-xl border bg-card p-5 shadow-xs transition-all outline-none hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md focus-visible:ring-[3px] focus-visible:ring-ring/50"
    >
      <div className="flex items-start gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/15 transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
          <FolderOpenIcon className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="truncate font-medium" title={collection.name}>{collection.name}</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {count} {count === 1 ? "item" : "items"}
          </p>
        </div>
        <ArrowUpRightIcon className="size-4 shrink-0 text-muted-foreground opacity-0 transition-all group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:opacity-100" />
      </div>

      <div className="mt-auto flex flex-wrap items-center gap-1.5">
        {kinds.length ? kinds.map((k) => {
          const Icon = KIND_ICONS[k];
          return (
            <Tooltip key={k}>
              <TooltipTrigger asChild>
                <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 tabular-nums", KIND_TONES[k])}>
                  <Icon className="size-3" />
                  {collection.materials[k].length}
                </span>
              </TooltipTrigger>
              <TooltipContent>{KIND_LABELS[k].many}</TooltipContent>
            </Tooltip>
          );
        }) : (
          <span className="text-xs text-muted-foreground italic">Empty</span>
        )}
      </div>

      <div className="flex items-center gap-1.5 border-t pt-3 text-xs text-muted-foreground">
        <CalendarIcon className="size-3.5" />
        Created {formatDate(collection.created_date)}
      </div>
    </Link>
  );
}

function CardSkeleton() {
  return (
    <div className="flex flex-col gap-4 rounded-xl border bg-card p-5 shadow-xs">
      <div className="flex items-start gap-3">
        <Skeleton className="size-10 rounded-lg" />
        <div className="flex flex-1 flex-col gap-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/3" />
        </div>
      </div>
      <div className="flex gap-1.5">
        <Skeleton className="h-5 w-10 rounded-full" />
        <Skeleton className="h-5 w-10 rounded-full" />
      </div>
      <Skeleton className="h-3 w-1/2" />
    </div>
  );
}

const GRID = "grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4";

export default function CollectionsPage() {
  const router = useRouter();
  const { data: collections = [], isPending, error } = useCollections();
  const create = useCreateCollection();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");

  const submit = () => {
    const trimmed = name.trim();
    if (!trimmed || create.isPending) return;
    create.mutate({ name: trimmed, materials: emptyMaterials() }, {
      onSuccess: (col) => {
        toast.success(`Created “${trimmed}”`);
        router.push(`/collections/${col.collection_id}`);
      },
    });
  };

  const newButton = (
    <Button onClick={() => setOpen(true)}>
      <PlusIcon />
      New collection
    </Button>
  );

  return (
    <AppShell>
      <PageContainer>
        <PageHeader
          icon={LibraryIcon}
          title="Collections"
          description="Group book sections, lectures, slides and notes, then study and chat over them together."
          actions={newButton}
        />

        {error && <ErrorAlert title="Failed to load collections">{errorMessage(error)}</ErrorAlert>}

        {isPending ? (
          <div className={GRID}>
            {[0, 1, 2, 3].map((i) => <CardSkeleton key={i} />)}
          </div>
        ) : !error && collections.length === 0 ? (
          <EmptyState
            icon={FolderOpenIcon}
            title="No collections yet"
            description={<>Create one, or use &ldquo;Add to collection&rdquo; on any section or upload.</>}
            className="border bg-card/50"
          >
            {newButton}
          </EmptyState>
        ) : (
          <div className={GRID}>
            {collections.map((c) => <CollectionCard key={c.collection_id} collection={c} />)}
          </div>
        )}
      </PageContainer>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <form
            className="grid gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              submit();
            }}
          >
            <DialogHeader>
              <DialogTitle>New collection</DialogTitle>
              <DialogDescription>Give it a name — you can add materials next.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-2">
              <Label htmlFor="collection-name">Name</Label>
              <Input
                id="collection-name"
                autoFocus
                placeholder="e.g. Midterm review"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            {create.error && <ErrorAlert>{errorMessage(create.error)}</ErrorAlert>}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={!name.trim() || create.isPending}>
                {create.isPending && <Spinner />}
                Create
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
