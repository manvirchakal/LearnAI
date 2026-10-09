"use client";
import {
  CheckIcon, ChevronLeftIcon, FolderOpenIcon, GamepadIcon, ListIcon, MessagesSquareIcon, NetworkIcon, PencilIcon,
  PlusIcon, Trash2Icon, XIcon,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useState } from "react";
import { toast } from "sonner";
import MaterialList, { KIND_ICONS, KIND_TONES } from "@/components/collections/MaterialList";
import MaterialPicker from "@/components/collections/MaterialPicker";
import AppShell from "@/components/layout/AppShell";
import { PageContainer } from "@/components/shared/PageHeader";
import { EmptyState, ErrorAlert, LoadingState } from "@/components/shared/States";
import ChatPanel from "@/components/study/ChatPanel";
import DiagramPanel from "@/components/study/DiagramPanel";
import GamePanel from "@/components/study/GamePanel";
import NarrativePanel from "@/components/study/NarrativePanel";
import StudyLayout from "@/components/study/StudyLayout";
import { StudySessionProvider } from "@/components/study/StudySession";
import {
  AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { errorMessage } from "@/api/client";
import { useCollection, useDeleteCollection, useRenameCollection } from "@/api/collections";
import { collectionUnit } from "@/api/study";
import { formatDate, KIND_LABELS } from "@/lib/materials";
import { cn } from "@/lib/utils";
import { MATERIAL_KINDS, materialCount, type Collection } from "@/types/collection";

function Title({ collection }: { collection: Collection }) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(collection.name);
  const rename = useRenameCollection(collection.collection_id);

  const save = () => {
    const trimmed = name.trim();
    if (!trimmed || trimmed === collection.name) return setEditing(false);
    rename.mutate(trimmed, {
      onSuccess: () => {
        setEditing(false);
        toast.success("Collection renamed");
      },
    });
  };

  if (editing) {
    return (
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-1.5">
          <Input
            value={name}
            autoFocus
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") setEditing(false); }}
            aria-label="Collection name"
            aria-invalid={!!rename.error}
            className="h-9 max-w-md text-base font-semibold"
          />
          <Button size="icon-sm" onClick={save} aria-label="Save name" disabled={rename.isPending}>
            {rename.isPending ? <Spinner /> : <CheckIcon />}
          </Button>
          <Button size="icon-sm" variant="ghost" onClick={() => setEditing(false)} aria-label="Cancel rename">
            <XIcon />
          </Button>
        </div>
        {rename.error && <p className="text-xs text-destructive">{errorMessage(rename.error)}</p>}
      </div>
    );
  }
  return (
    <div className="group flex min-w-0 items-center gap-1">
      <h1 className="truncate text-xl font-semibold tracking-tight sm:text-2xl" title={collection.name}>
        {collection.name}
      </h1>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            size="icon-sm"
            variant="ghost"
            className="shrink-0 text-muted-foreground sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100"
            onClick={() => { setName(collection.name); setEditing(true); }}
            aria-label="Rename"
          >
            <PencilIcon />
          </Button>
        </TooltipTrigger>
        <TooltipContent>Rename</TooltipContent>
      </Tooltip>
    </div>
  );
}

export default function CollectionPage({ params }: { params: Promise<{ collectionId: string }> }) {
  const { collectionId } = use(params);
  const router = useRouter();
  const { data: collection, isPending, error } = useCollection(collectionId);
  const del = useDeleteCollection();
  const [picking, setPicking] = useState(false);
  const [confirming, setConfirming] = useState(false);

  if (isPending) {
    return <AppShell><LoadingState label="Loading collection…" fullPage /></AppShell>;
  }
  if (!collection) {
    return (
      <AppShell>
        <PageContainer>
          <ErrorAlert
            title="Couldn't load this collection"
            action={<Button size="sm" variant="outline" asChild><Link href="/collections">Back to collections</Link></Button>}
          >
            {errorMessage(error)}
          </ErrorAlert>
        </PageContainer>
      </AppShell>
    );
  }

  const count = materialCount(collection.materials);
  const unit = collectionUnit(collectionId);
  const kinds = MATERIAL_KINDS.filter((k) => collection.materials[k].length);

  return (
    <AppShell mobileNav={false}>
      <StudySessionProvider key={unit} unit={unit} autoGenerate={false}>
        <StudyLayout
          guide={
            <>
            <header className="border-b bg-gradient-to-b from-primary/5 to-transparent px-4 pt-4 pb-5 sm:px-6">
              <Link
                href="/collections"
                className="mb-3 inline-flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
              >
                <ChevronLeftIcon className="size-3.5" />
                Collections
              </Link>
              <div className="flex items-start gap-3">
                <span className="mt-0.5 hidden size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/15 sm:flex">
                  <FolderOpenIcon className="size-5" />
                </span>
                <div className="min-w-0 flex-1">
                  <Title key={collection.name} collection={collection} />
                  <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                    <Badge variant="secondary" className="tabular-nums">
                      {count} {count === 1 ? "item" : "items"}
                    </Badge>
                    {kinds.map((k) => {
                      const Icon = KIND_ICONS[k];
                      return (
                        <span
                          key={k}
                          title={KIND_LABELS[k].many}
                          className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium ring-1 tabular-nums", KIND_TONES[k])}
                        >
                          <Icon className="size-3" />
                          {collection.materials[k].length}
                        </span>
                      );
                    })}
                    <span className="ml-1">Created {formatDate(collection.created_date)}</span>
                  </div>
                </div>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="shrink-0 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                      onClick={() => setConfirming(true)}
                      aria-label="Delete collection"
                    >
                      <Trash2Icon />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Delete collection</TooltipContent>
                </Tooltip>
              </div>
            </header>
            {count ? (
              <NarrativePanel />
            ) : (
              <EmptyState
                icon={FolderOpenIcon}
                title="This collection is empty"
                description="Add book sections, transcripts, slides or notes to study them together."
                className="m-4 border sm:m-6"
              >
                <Button onClick={() => setPicking(true)}>
                  <PlusIcon />
                  Add materials
                </Button>
              </EmptyState>
            )}
            </>
          }
          views={[
            {
              value: "materials",
              label: "Materials",
              icon: ListIcon,
              badge: count,
              content: <MaterialList collection={collection} onEdit={() => setPicking(true)} />,
            },
            { value: "chat", label: "Chat", icon: MessagesSquareIcon, fill: true, content: <ChatPanel unit={unit} subject="this collection" /> },
            { value: "game", label: "Game", icon: GamepadIcon, content: <GamePanel /> },
            { value: "diagram", label: "Diagrams", icon: NetworkIcon, content: <DiagramPanel /> },
          ]}
        />
      </StudySessionProvider>

      <MaterialPicker collection={collection} open={picking} onClose={() => setPicking(false)} />

      <AlertDialog open={confirming} onOpenChange={setConfirming}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete collection?</AlertDialogTitle>
            <AlertDialogDescription>
              &ldquo;{collection.name}&rdquo;, its study guide and chat history will be removed. The books and media
              in it are kept.
            </AlertDialogDescription>
          </AlertDialogHeader>
          {del.error && <ErrorAlert>{errorMessage(del.error)}</ErrorAlert>}
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <Button
              variant="destructive"
              disabled={del.isPending}
              onClick={() => del.mutate(collectionId, {
                onSuccess: () => {
                  toast.success(`Deleted “${collection.name}”`);
                  router.push("/collections");
                },
              })}
            >
              {del.isPending ? <Spinner /> : <Trash2Icon />}
              Delete
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}
