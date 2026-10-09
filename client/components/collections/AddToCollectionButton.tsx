"use client";
import { CheckIcon, FolderIcon, ListPlusIcon, PlusIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ErrorAlert } from "@/components/shared/States";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { errorMessage } from "@/api/client";
import { useCollections, useCreateCollection, useUpdateCollectionMaterials } from "@/api/collections";
import { hasMaterial, withMaterial, type MaterialRef } from "@/lib/materials";
import { cn } from "@/lib/utils";
import { emptyMaterials, materialCount, type Collection, type MaterialKind } from "@/types/collection";

interface Props {
  kind: MaterialKind;
  item: MaterialRef;
  size?: "small" | "medium";
}

/** Adds one material to an existing collection, or to a new one. */
export default function AddToCollectionButton({ kind, item, size = "small" }: Props) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const collections = useCollections();
  const update = useUpdateCollectionMaterials();
  const create = useCreateCollection();
  const error = update.error ?? create.error ?? collections.error;

  const add = (col: Collection) => {
    if (hasMaterial(col.materials, kind, item)) return;
    update.mutate(
      { collectionId: col.collection_id, materials: withMaterial(col.materials, kind, item) },
      { onSuccess: () => toast.success(`Added to “${col.name}”`) },
    );
  };

  const createWithItem = () => {
    const trimmed = name.trim();
    if (!trimmed || create.isPending) return;
    create.mutate(
      { name: trimmed, materials: withMaterial(emptyMaterials(), kind, item) },
      {
        onSuccess: () => {
          setName("");
          toast.success(`Created “${trimmed}”`);
        },
      },
    );
  };

  return (
    <>
      <Button size={size === "small" ? "sm" : "default"} variant="outline" onClick={() => setOpen(true)}>
        <ListPlusIcon />
        Add to collection
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add to collection</DialogTitle>
            <DialogDescription>Pick a collection, or start a new one with this item.</DialogDescription>
          </DialogHeader>

          {error && <ErrorAlert>{errorMessage(error)}</ErrorAlert>}

          {collections.isPending ? (
            <div className="flex flex-col gap-2">
              {[0, 1, 2].map((i) => <Skeleton key={i} className="h-12 w-full rounded-lg" />)}
            </div>
          ) : collections.data?.length ? (
            <ul className="-mx-1 flex max-h-80 flex-col gap-1 overflow-y-auto px-1">
              {collections.data.map((col) => {
                const added = hasMaterial(col.materials, kind, item);
                const busy = update.isPending && update.variables?.collectionId === col.collection_id;
                const count = materialCount(col.materials);
                return (
                  <li key={col.collection_id}>
                    <button
                      type="button"
                      onClick={() => add(col)}
                      disabled={busy || added}
                      className={cn(
                        "flex w-full items-center gap-3 rounded-lg border border-transparent px-3 py-2 text-left transition-colors outline-none",
                        "hover:border-border hover:bg-accent/60 focus-visible:ring-[3px] focus-visible:ring-ring/50",
                        "disabled:pointer-events-none",
                        busy && "opacity-60",
                        added && "border-primary/20 bg-primary/5",
                      )}
                    >
                      <span
                        className={cn(
                          "flex size-8 shrink-0 items-center justify-center rounded-md ring-1",
                          added ? "bg-primary text-primary-foreground ring-primary" : "bg-muted text-muted-foreground ring-border",
                        )}
                      >
                        {busy ? <Spinner /> : added ? <CheckIcon className="size-4" /> : <FolderIcon className="size-4" />}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium">{col.name}</span>
                        <span className="block text-xs text-muted-foreground">
                          {added ? "Already added" : `${count} ${count === 1 ? "item" : "items"}`}
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : (
            <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
              You don&apos;t have any collections yet.
            </div>
          )}

          <Separator />

          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              createWithItem();
            }}
          >
            <Input
              placeholder="New collection name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              aria-label="New collection name"
            />
            <Button type="submit" disabled={!name.trim() || create.isPending}>
              {create.isPending ? <Spinner /> : <PlusIcon />}
              Create
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
