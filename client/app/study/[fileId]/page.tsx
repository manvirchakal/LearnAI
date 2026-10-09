"use client";
import { BookOpenIcon, ChevronRightIcon, FileTextIcon, LayersIcon, ListTreeIcon } from "lucide-react";
import Link from "next/link";
import { use } from "react";
import AppShell from "@/components/layout/AppShell";
import PageHeader, { PageContainer } from "@/components/shared/PageHeader";
import { EmptyState, ErrorAlert } from "@/components/shared/States";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useBook } from "@/api/books";
import { errorMessage } from "@/api/client";

function OverviewSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <div className="mb-4 flex items-start gap-3">
        <Skeleton className="size-10 rounded-xl" />
        <div className="flex flex-1 flex-col gap-2">
          <Skeleton className="h-7 w-2/3" />
          <Skeleton className="h-4 w-1/3" />
        </div>
      </div>
      {Array.from({ length: 3 }, (_, i) => (
        <div key={i} className="rounded-xl border bg-card shadow-xs">
          <div className="flex items-center gap-3 border-b px-5 py-4">
            <Skeleton className="size-8 rounded-lg" />
            <Skeleton className="h-5 w-1/2" />
          </div>
          <div className="flex flex-col gap-3 p-5">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function BookOverviewPage({ params }: { params: Promise<{ fileId: string }> }) {
  const { fileId } = use(params);
  const { data: book, isPending, error } = useBook(fileId);

  return (
    <AppShell book={book}>
      <PageContainer className="max-w-4xl">
        {isPending && <OverviewSkeleton />}
        {error && <ErrorAlert title="Couldn't load this book">{errorMessage(error)}</ErrorAlert>}
        {book && (
          <>
            <PageHeader
              icon={BookOpenIcon}
              eyebrow="Book overview"
              title={book.title}
              description={
                <span className="mt-2 flex flex-wrap gap-1.5">
                  <Badge variant="secondary"><FileTextIcon />{book.num_pages} pages</Badge>
                  <Badge variant="secondary"><ListTreeIcon />{book.chapter_count} chapters</Badge>
                  <Badge variant="outline" className="border-primary/20 bg-primary/5 text-primary">
                    <LayersIcon />{book.section_count} sections
                  </Badge>
                </span>
              }
            />

            {book.chapters.length === 0 && (
              <EmptyState
                icon={ListTreeIcon}
                title="No chapters found"
                description="This book's structure couldn't be detected."
                className="rounded-xl border border-dashed"
              />
            )}

            <div className="flex flex-col gap-4">
              {book.chapters.map((chapter) => (
                <section
                  key={chapter.id}
                  className="overflow-hidden rounded-xl border bg-card shadow-xs transition hover:border-primary/30 hover:shadow-md"
                >
                  <header className="flex items-center gap-3 border-b bg-muted/30 px-4 py-3 sm:px-5">
                    <span className="flex h-8 min-w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 px-2 text-sm font-semibold text-primary ring-1 ring-primary/15 tabular-nums">
                      {chapter.number}
                    </span>
                    <div className="min-w-0 flex-1">
                      <h2 className="font-semibold tracking-tight text-pretty">{chapter.title}</h2>
                      <p className="text-xs text-muted-foreground">
                        Pages {chapter.start_page}–{chapter.end_page}
                      </p>
                    </div>
                    <Badge variant="secondary" className="hidden sm:inline-flex">
                      {chapter.sections.length} {chapter.sections.length === 1 ? "section" : "sections"}
                    </Badge>
                  </header>
                  <ul className="divide-y">
                    {chapter.sections.map((section) => (
                      <li key={section.id}>
                        <Link
                          href={`/study/${book.file_id}/${section.id}`}
                          className="group flex items-center gap-3 px-4 py-3 transition-colors outline-none hover:bg-accent/60 focus-visible:bg-accent sm:px-5"
                        >
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-pretty group-hover:text-primary">{section.title}</p>
                            <p className="text-xs text-muted-foreground">
                              Pages {section.start_page}–{section.end_page}
                            </p>
                          </div>
                          <ChevronRightIcon className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
                        </Link>
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
            </div>
          </>
        )}
      </PageContainer>
    </AppShell>
  );
}
