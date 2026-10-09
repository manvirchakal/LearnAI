"use client";
import { BookOpenIcon, FileTextIcon, Gamepad2Icon, MessagesSquareIcon, WorkflowIcon } from "lucide-react";
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
import SectionPager from "@/components/study/SectionPager";
import StudyLayout from "@/components/study/StudyLayout";
import { Badge } from "@/components/ui/badge";
import { sectionPdfUrl, useBook } from "@/api/books";
import { sectionUnit } from "@/api/study";

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
    <AppShell book={book} activeSectionId={sectionId} mobileNav={false}>
      <StudySessionProvider key={unit} unit={unit}>
        <StudyLayout
          guide={
            <>
              <header className="border-b bg-gradient-to-b from-accent/40 to-transparent px-4 pt-5 pb-4 sm:px-8 sm:pt-6 sm:pb-5">
                <div className="mx-auto flex max-w-3xl items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <nav className="mb-2 flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
                      <BookOpenIcon className="size-3.5 shrink-0" />
                      <Link href={`/study/${fileId}`} className="truncate hover:text-foreground">{book.title}</Link>
                      <span>/</span>
                      <span className="truncate">{chapter?.title}</span>
                    </nav>
                    <h1 className="text-xl font-semibold tracking-tight text-balance sm:text-2xl">{section.title}</h1>
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {chapter?.number && <Badge variant="secondary">{chapter.number}</Badge>}
                      <Badge variant="outline" className="font-mono">pp. {section.start_page}–{section.end_page}</Badge>
                    </div>
                  </div>
                  <AddToCollectionButton
                    kind="textbook_sections"
                    item={{ file_id: fileId, section_id: sectionId, title: `${book.title}: ${section.title}` }}
                  />
                </div>
              </header>
              <NarrativePanel />
              <SectionPager book={book} sectionId={sectionId} />
            </>
          }
          views={[
            { value: "chat", label: "Chat", icon: MessagesSquareIcon, fill: true, content: <ChatPanel unit={unit} /> },
            { value: "game", label: "Game", icon: Gamepad2Icon, content: <GamePanel /> },
            { value: "diagram", label: "Diagrams", icon: WorkflowIcon, content: <DiagramPanel /> },
            {
              value: "pdf",
              label: "PDF",
              icon: FileTextIcon,
              content: <PDFViewer key={sectionId} url={sectionPdfUrl(fileId, sectionId)} firstPage={section.start_page} />,
            },
          ]}
        />
      </StudySessionProvider>
    </AppShell>
  );
}
