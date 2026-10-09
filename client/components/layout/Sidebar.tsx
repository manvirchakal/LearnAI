"use client";
import { ChevronRightIcon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { useIsMobile } from "@/hooks/use-mobile";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/store/uiStore";
import type { BookDetail } from "@/types/book";

interface Props {
  book: BookDetail;
  activeSectionId?: string;
}

function BookContents({ book, activeSectionId, onNavigate }: Props & { onNavigate?: () => void }) {
  const activeChapter = book.chapters.find((c) => c.sections.some((s) => s.id === activeSectionId))?.id;
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set(activeChapter ? [activeChapter] : []));

  const setOpen = (id: string, open: boolean) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (open) next.add(id);
      else next.delete(id);
      return next;
    });

  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-4 py-4">
        <Link href={`/study/${book.file_id}`} onClick={onNavigate} className="block truncate font-semibold tracking-tight hover:text-primary" title={book.title}>
          {book.title}
        </Link>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {book.section_count} sections · {book.num_pages} pages
        </p>
      </div>
      <ScrollArea className="min-h-0 flex-1">
        <nav className="space-y-0.5 p-2">
          {book.chapters.map((chapter) => {
            const open = expanded.has(chapter.id);
            return (
              <Collapsible key={chapter.id} open={open} onOpenChange={(o) => setOpen(chapter.id, o)}>
                <CollapsibleTrigger className="group flex w-full items-start gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-sidebar-accent">
                  <ChevronRightIcon
                    className={cn("mt-0.5 size-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-90")}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
                      {chapter.number}
                    </span>
                    <span className="block leading-snug font-medium">{chapter.title}</span>
                  </span>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div className="my-1 ml-[1.1rem] space-y-0.5 border-l pl-2">
                    {chapter.sections.map((section) => {
                      const active = section.id === activeSectionId;
                      return (
                        <Link
                          key={section.id}
                          href={`/study/${book.file_id}/${section.id}`}
                          onClick={onNavigate}
                          className={cn(
                            "block rounded-md px-2 py-1.5 text-[13px] leading-snug text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                            active && "bg-sidebar-accent font-medium text-sidebar-accent-foreground",
                          )}
                        >
                          {section.title}
                          <span className="mt-0.5 block text-[11px] opacity-70">
                            pp. {section.start_page}–{section.end_page}
                          </span>
                        </Link>
                      );
                    })}
                  </div>
                </CollapsibleContent>
              </Collapsible>
            );
          })}
        </nav>
      </ScrollArea>
    </div>
  );
}

/** The book's table of contents: a collapsible rail on desktop, a sheet on mobile. */
export default function Sidebar(props: Props) {
  const { sidebarOpen, tocSheetOpen, setTocSheetOpen } = useUIStore();
  const isMobile = useIsMobile();

  if (isMobile) {
    return (
      <Sheet open={tocSheetOpen} onOpenChange={setTocSheetOpen}>
        <SheetContent side="left" className="w-80 bg-sidebar p-0">
          <SheetTitle className="sr-only">Contents</SheetTitle>
          <BookContents {...props} onNavigate={() => setTocSheetOpen(false)} />
        </SheetContent>
      </Sheet>
    );
  }

  return (
    <aside
      className={cn(
        "sticky top-14 h-[calc(100svh-3.5rem)] shrink-0 overflow-hidden border-r bg-sidebar text-sidebar-foreground transition-[width] duration-200 ease-out",
        sidebarOpen ? "w-72" : "w-0 border-r-0",
      )}
    >
      <div className="h-full w-72">
        <BookContents {...props} />
      </div>
    </aside>
  );
}
