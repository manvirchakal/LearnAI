"use client";
import { BookOpenIcon, FileTextIcon, LayersIcon, Trash2Icon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useDeleteBook } from "@/api/books";
import { errorMessage } from "@/api/client";
import type { BookSummary } from "@/types/book";

export default function BookCard({ book }: { book: BookSummary }) {
  const [confirming, setConfirming] = useState(false);
  const del = useDeleteBook();

  const handleDelete = () =>
    del.mutate(book.file_id, {
      onSuccess: () => {
        setConfirming(false);
        toast.success(`Deleted “${book.title}”`);
      },
      onError: (err) => toast.error(`Couldn't delete book: ${errorMessage(err)}`),
    });

  return (
    <>
      <div className="group relative flex h-full items-start gap-2 rounded-xl border bg-card p-4 shadow-xs transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md">
        <Link
          href={`/study/${book.file_id}`}
          className="flex min-w-0 flex-1 gap-4 rounded-md outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
        >
          <div className="relative flex h-16 w-12 shrink-0 items-center justify-center overflow-hidden rounded-md bg-gradient-to-br from-primary/15 to-chart-2/15 text-primary ring-1 ring-primary/15">
            <span aria-hidden className="absolute inset-y-0 left-0 w-1 bg-primary/30" />
            <BookOpenIcon className="size-5" />
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="truncate font-medium tracking-tight group-hover:text-primary" title={book.title}>
              {book.title}
            </h3>
            {book.filename && book.filename !== book.title && (
              <p className="truncate text-xs text-muted-foreground" title={book.filename}>{book.filename}</p>
            )}
            <div className="mt-2 flex flex-wrap gap-1.5">
              <Badge variant="secondary">
                <FileTextIcon />
                {book.num_pages} pages
              </Badge>
              <Badge variant="outline" className="border-primary/20 bg-primary/5 text-primary">
                <LayersIcon />
                {book.section_count} sections
              </Badge>
            </div>
          </div>
        </Link>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              className="shrink-0 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
              onClick={() => setConfirming(true)}
              aria-label={`Delete ${book.title}`}
            >
              <Trash2Icon />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Delete</TooltipContent>
        </Tooltip>
      </div>

      <AlertDialog open={confirming} onOpenChange={(open) => !del.isPending && setConfirming(open)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogMedia className="bg-destructive/10 text-destructive">
              <Trash2Icon />
            </AlertDialogMedia>
            <AlertDialogTitle>Delete book?</AlertDialogTitle>
            <AlertDialogDescription>
              &ldquo;{book.title}&rdquo; and its generated study materials and chat history will be removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={del.isPending}>Cancel</AlertDialogCancel>
            {/* Plain Button (not AlertDialogAction) so the dialog stays open until the delete finishes */}
            <Button variant="destructive" disabled={del.isPending} onClick={handleDelete}>
              {del.isPending && <Spinner />}
              Delete
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
