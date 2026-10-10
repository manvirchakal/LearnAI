"use client";
import { BookOpenIcon, UploadIcon } from "lucide-react";
import Link from "next/link";
import BookCard from "./BookCard";
import { EmptyState } from "@/components/shared/States";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { BookSummary } from "@/types/book";

interface Props {
  books: BookSummary[];
}

const gridClass = "grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3";

export default function BookGrid({ books }: Props) {
  if (books.length === 0) {
    return (
      <EmptyState
        icon={BookOpenIcon}
        title="No books yet"
        description="Upload a PDF to get started."
        className="rounded-xl border border-dashed"
      >
        <Button asChild>
          <Link href="/upload">
            <UploadIcon />
            Upload a PDF
          </Link>
        </Button>
      </EmptyState>
    );
  }

  return (
    <div className={gridClass}>
      {books.map((book) => (
        <BookCard key={book.file_id} book={book} />
      ))}
    </div>
  );
}

export function BookGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className={gridClass}>
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="flex gap-4 rounded-xl border bg-card p-4 shadow-xs">
          <Skeleton className="h-16 w-12 shrink-0 rounded-md" />
          <div className="flex flex-1 flex-col gap-2 pt-1">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/3" />
            <div className="mt-1 flex gap-1.5">
              <Skeleton className="h-5 w-16 rounded-full" />
              <Skeleton className="h-5 w-20 rounded-full" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
