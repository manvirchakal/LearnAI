"use client";
import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";
import Link from "next/link";
import type { BookDetail } from "@/types/book";

/** Previous / next section at the end of the guide, so phones needn't open the contents to move on */
export default function SectionPager({ book, sectionId }: { book: BookDetail; sectionId: string }) {
  const sections = book.chapters.flatMap((c) => c.sections);
  const i = sections.findIndex((s) => s.id === sectionId);
  const prev = sections[i - 1];
  const next = sections[i + 1];
  if (!prev && !next) return null;

  const href = (id: string) => `/study/${book.file_id}/${encodeURIComponent(id)}`;
  const card =
    "group flex min-w-0 flex-1 items-center gap-2 rounded-xl border bg-card p-3 text-sm shadow-xs transition-colors hover:border-primary/40 hover:bg-accent/50";

  return (
    <nav aria-label="Sections" className="mx-auto flex max-w-3xl gap-2 px-4 pt-2 pb-8 sm:px-8">
      {prev ? (
        <Link href={href(prev.id)} className={card}>
          <ChevronLeftIcon className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:-translate-x-0.5" />
          <span className="min-w-0">
            <span className="block text-xs text-muted-foreground">Previous</span>
            <span className="block truncate font-medium">{prev.title}</span>
          </span>
        </Link>
      ) : <span className="flex-1" />}
      {next ? (
        <Link href={href(next.id)} className={`${card} justify-end text-right`}>
          <span className="min-w-0">
            <span className="block text-xs text-muted-foreground">Next</span>
            <span className="block truncate font-medium">{next.title}</span>
          </span>
          <ChevronRightIcon className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
        </Link>
      ) : <span className="flex-1" />}
    </nav>
  );
}
