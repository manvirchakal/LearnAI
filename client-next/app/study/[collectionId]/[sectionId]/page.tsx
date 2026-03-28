"use client";
import { Box, Typography, Divider } from "@mui/material";
import { use, useEffect } from "react";
import AppShell from "@/components/layout/AppShell";
import NarrativePanel from "@/components/study/NarrativePanel";
import GamePanel from "@/components/study/GamePanel";
import DiagramPanel from "@/components/study/DiagramPanel";
import ChatPanel from "@/components/study/ChatPanel";
import PDFViewer from "@/components/study/PDFViewer";
import StudyTabs from "@/components/study/StudyTabs";
import Spinner from "@/components/ui/Spinner";
import { useStudyStore } from "@/store/studyStore";
import { useUIStore } from "@/store/uiStore";
import { useTextbookStructure } from "@/api/textbooks";

interface PageProps {
  params: Promise<{ collectionId: string; sectionId: string }>;
}

export default function StudyPage({ params }: PageProps) {
  const { collectionId, sectionId } = use(params);
  const decodedSection = decodeURIComponent(sectionId);

  const { setStudyContext, setChapters, fileId, userId } = useStudyStore();
  const { activeTab } = useUIStore();

  // Derive fileId from collectionId — collectionId may be the fileId itself
  const effectiveFileId = fileId || collectionId;

  const { data: structure, isLoading } = useTextbookStructure(userId, effectiveFileId, decodedSection);

  useEffect(() => {
    setStudyContext(collectionId, decodedSection, effectiveFileId);
  }, [collectionId, decodedSection, effectiveFileId]);

  useEffect(() => {
    if (structure?.chapters) {
      setChapters(structure.chapters);
    }
  }, [structure]);

  // Build collectionIdMap: sectionTitle → collectionId from structure
  const collectionIdMap: Record<string, string> = {};
  if (structure?.chapters) {
    structure.chapters.forEach((ch) => {
      ch.sections.forEach((sec) => {
        collectionIdMap[sec.title] = sec.id;
      });
    });
  }

  const pdfUrl = `/api-backend/get-section-pdf?user_id=${userId}&file_id=${effectiveFileId}&section_name=${encodeURIComponent(decodedSection)}`;

  return (
    <AppShell
      chapters={structure?.chapters || []}
      collectionIdMap={collectionIdMap}
      fileId={effectiveFileId}
    >
      <Box sx={{ display: "flex", height: "calc(100vh - 64px)" }}>
        {/* Left: Narrative */}
        <Box sx={{ flex: 1, overflowY: "auto", borderRight: "1px solid #e9ecef" }}>
          <Box sx={{ p: 3, pb: 1 }}>
            <Typography variant="h6" fontWeight={700}>
              {decodedSection}
            </Typography>
          </Box>
          <Divider />
          {isLoading ? (
            <Box sx={{ p: 4 }}><Spinner label="Loading section…" /></Box>
          ) : (
            <NarrativePanel />
          )}
        </Box>

        {/* Right: Interactive panel */}
        <Box sx={{ width: 480, flexShrink: 0, display: "flex", flexDirection: "column", overflowY: "auto" }}>
          <StudyTabs />
          <Box sx={{ flex: 1, overflowY: "auto" }}>
            {activeTab === "game" && <GamePanel />}
            {activeTab === "diagram" && <DiagramPanel />}
            {activeTab === "pdf" && <PDFViewer pdfUrl={pdfUrl} />}
          </Box>
          <Divider />
          <ChatPanel />
        </Box>
      </Box>
    </AppShell>
  );
}
