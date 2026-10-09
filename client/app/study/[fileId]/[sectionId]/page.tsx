"use client";
import { BookOpenIcon } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { use } from "react";
import AddToCollectionButton from "@/components/collections/AddToCollectionButton";
import AppShell from "@/components/layout/AppShell";
import { ErrorAlert, LoadingState } from "@/components/shared/States";
import ChatPanel from "@/components/study/ChatPanel";
import DiagramPanel from "@/components/study/DiagramPanel";
import GamePanel from "@/components/study/GamePanel";
import NarrativePanel from "@/components/study/NarrativePanel";
import { StudySessionProvider } from "@/components/study/StudySession";
import StudyTabs from "@/components/study/StudyTabs";
import { Badge } from "@/components/ui/badge";
import { sectionPdfUrl, useBook } from "@/api/books";
import { sectionUnit } from "@/api/study";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/store/uiStore";

// react-pdf touches browser-only APIs at import time
const PDFViewer = dynamic(() => import("@/components/study/PDFViewer"), {
  ssr: false,
  loading: () => <LoadingState label="Loading viewer…" />,
});

interface PageProps {
  params: Promise<{ fileId: string; sectionId: string }>;
}

export default function StudyPage({ params }: PageProps) {
  const { fileId, sectionId: rawSectionId } = use(params);
  const sectionId = decodeURIComponent(rawSectionId);
  const { activeTab } = useUIStore();
  const { data: book, isPending } = useBook(fileId);

  const chapter = book?.chapters.find((c) => c.sections.some((s) => s.id === sectionId));
  const section = chapter?.sections.find((s) => s.id === sectionId);

  if (isPending) {
    return (
      <AppShell>
        <LoadingState label="Loading section…" fullPage />
      </AppShell>
    );
  }
  if (!book || !section) {
    return (
      <AppShell book={book}>
        <div className="p-6">
          <ErrorAlert title="Not found">This section doesn&apos;t exist.</ErrorAlert>
        </div>
      </AppShell>
    );
  }

  const unit = sectionUnit(fileId, sectionId);

  return (
    <AppShell book={book} activeSectionId={sectionId}>
      <StudySessionProvider key={unit} unit={unit}>
        <div className="flex flex-col lg:h-[calc(100svh-3.5rem)] lg:flex-row">
          <div className="min-w-0 flex-1 lg:overflow-y-auto">
            <header className="border-b bg-gradient-to-b from-accent/40 to-transparent px-4 pt-6 pb-5 sm:px-8">
              <div className="mx-auto flex max-w-3xl flex-col gap-4 sm:flex-row sm:items-start">
                <div className="min-w-0 flex-1">
                  <nav className="mb-2 flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
                    <BookOpenIcon className="size-3.5 shrink-0" />
                    <Link href={`/study/${fileId}`} className="truncate hover:text-foreground">{book.title}</Link>
                    <span>/</span>
                    <span className="truncate">{chapter?.title}</span>
                  </nav>
                  <h1 className="text-2xl font-semibold tracking-tight text-balance">{section.title}</h1>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {chapter?.number && <Badge variant="secondary">{chapter.number}</Badge>}
                    <Badge variant="outline">pp. {section.start_page}–{section.end_page}</Badge>
                  </div>
                </div>
                <AddToCollectionButton
                  kind="textbook_sections"
                  item={{ file_id: fileId, section_id: sectionId, title: `${book.title}: ${section.title}` }}
                />
              </div>
            </header>
            <NarrativePanel />
          </div>

          <aside className="flex h-[85svh] w-full shrink-0 flex-col border-t bg-card/50 lg:h-auto lg:w-[460px] lg:border-t-0 lg:border-l xl:w-[520px]">
            <StudyTabs />
            <div className={cn("min-h-0 flex-1", activeTab === "chat" ? "overflow-hidden" : "overflow-y-auto")}>
              {activeTab === "chat" && <ChatPanel unit={unit} />}
              {activeTab === "game" && <GamePanel />}
              {activeTab === "diagram" && <DiagramPanel />}
              {activeTab === "pdf" && (
                <PDFViewer key={sectionId} url={sectionPdfUrl(fileId, sectionId)} firstPage={section.start_page} />
              )}
            </div>
          </aside>
        </div>
      </StudySessionProvider>
    </AppShell>
  );
}
