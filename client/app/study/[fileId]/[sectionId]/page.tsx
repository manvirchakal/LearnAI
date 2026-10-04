"use client";
import { Alert, Box, Divider, Typography } from "@mui/material";
import dynamic from "next/dynamic";
import AddToCollectionButton from "@/components/collections/AddToCollectionButton";
import AppShell from "@/components/layout/AppShell";
import ChatPanel from "@/components/study/ChatPanel";
import DiagramPanel from "@/components/study/DiagramPanel";
import GamePanel from "@/components/study/GamePanel";
import NarrativePanel from "@/components/study/NarrativePanel";
import { StudySessionProvider } from "@/components/study/StudySession";
import StudyTabs from "@/components/study/StudyTabs";
import Spinner from "@/components/ui/Spinner";
import { sectionPdfUrl, useBook } from "@/api/books";
import { sectionUnit } from "@/api/study";
import { useUIStore } from "@/store/uiStore";

// react-pdf touches browser-only APIs at import time
const PDFViewer = dynamic(() => import("@/components/study/PDFViewer"), {
  ssr: false,
  loading: () => <Spinner label="Loading viewer…" />,
});

interface PageProps {
  params: { fileId: string; sectionId: string };
}

export default function StudyPage({ params }: PageProps) {
  const { fileId } = params;
  const sectionId = decodeURIComponent(params.sectionId);
  const { activeTab } = useUIStore();
  const { data: book, isPending } = useBook(fileId);

  const chapter = book?.chapters.find((c) => c.sections.some((s) => s.id === sectionId));
  const section = chapter?.sections.find((s) => s.id === sectionId);

  if (isPending) {
    return (
      <AppShell>
        <Spinner label="Loading section…" fullPage />
      </AppShell>
    );
  }
  if (!book || !section) {
    return (
      <AppShell book={book}>
        <Box sx={{ p: 4 }}>
          <Alert severity="error">This section doesn&apos;t exist.</Alert>
        </Box>
      </AppShell>
    );
  }

  const unit = sectionUnit(fileId, sectionId);

  return (
    <AppShell book={book} activeSectionId={sectionId}>
      <StudySessionProvider key={unit} unit={unit}>
        <Box sx={{ display: "flex", height: "calc(100vh - 64px)" }}>
          <Box sx={{ flex: 1, minWidth: 0, overflowY: "auto", borderRight: "1px solid #e9ecef" }}>
            <Box sx={{ p: 3, pb: 1, display: "flex", alignItems: "flex-start", gap: 2 }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="caption" color="text.secondary">
                  {chapter?.number} · {chapter?.title} · pp. {section.start_page}–{section.end_page}
                </Typography>
                <Typography variant="h6" fontWeight={700}>
                  {section.title}
                </Typography>
              </Box>
              <AddToCollectionButton
                kind="textbook_sections"
                item={{ file_id: fileId, section_id: sectionId, title: `${book.title}: ${section.title}` }}
              />
            </Box>
            <Divider />
            <NarrativePanel />
          </Box>

          <Box sx={{ width: 480, flexShrink: 0, display: "flex", flexDirection: "column", bgcolor: "#fff" }}>
            <StudyTabs />
            <Box sx={{ flex: 1, minHeight: 0, overflowY: activeTab === "chat" ? "hidden" : "auto" }}>
              {activeTab === "chat" && <ChatPanel unit={unit} />}
              {activeTab === "game" && <GamePanel />}
              {activeTab === "diagram" && <DiagramPanel />}
              {activeTab === "pdf" && (
                <PDFViewer key={sectionId} url={sectionPdfUrl(fileId, sectionId)} firstPage={section.start_page} />
              )}
            </Box>
          </Box>
        </Box>
      </StudySessionProvider>
    </AppShell>
  );
}
