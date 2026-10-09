"use client";
import { LibraryIcon, UploadIcon } from "lucide-react";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import BookGrid, { BookGridSkeleton } from "@/components/library/BookGrid";
import PageHeader, { PageContainer } from "@/components/shared/PageHeader";
import { ErrorAlert } from "@/components/shared/States";
import { Button } from "@/components/ui/button";
import { useBooks } from "@/api/books";
import { errorMessage } from "@/api/client";

export default function LibraryPage() {
  const { data: books = [], isPending, error } = useBooks();

  return (
    <AppShell>
      <PageContainer>
        <PageHeader
          icon={LibraryIcon}
          title="My Library"
          description={isPending ? "Loading your books…" : `${books.length} ${books.length === 1 ? "book" : "books"}`}
          actions={
            <Button asChild>
              <Link href="/upload">
                <UploadIcon />
                Upload PDF
              </Link>
            </Button>
          }
        />
        {isPending && <BookGridSkeleton />}
        {error && <ErrorAlert title="Failed to load library">{errorMessage(error)}</ErrorAlert>}
        {!isPending && !error && <BookGrid books={books} />}
      </PageContainer>
    </AppShell>
  );
}
