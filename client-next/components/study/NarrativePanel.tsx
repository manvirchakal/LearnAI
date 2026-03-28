"use client";
import { Box, Typography, Alert, LinearProgress } from "@mui/material";
import { useEffect, useRef } from "react";
import MarkdownRenderer from "@/components/shared/MarkdownRenderer";
import Button from "@/components/ui/Button";
import Spinner from "@/components/ui/Spinner";
import { useStudyStore } from "@/store/studyStore";
import { useGenerateNarrative } from "@/api/content";

export default function NarrativePanel() {
  const { collectionId, sectionName, narrative, isStreamingNarrative, streamingText, forceRegenerate, setNarrative } = useStudyStore();
  const bottomRef = useRef<HTMLDivElement>(null);
  const { mutate: generate, isPending, error } = useGenerateNarrative();

  useEffect(() => {
    if (!collectionId || !sectionName) return;
    if (narrative && !forceRegenerate) return;
    generate({ collectionId, sectionName });
  }, [collectionId, sectionName, forceRegenerate]);

  // Auto-scroll during streaming
  useEffect(() => {
    if (isStreamingNarrative) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [streamingText, isStreamingNarrative]);

  if (!collectionId) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <Typography color="text.secondary">Select a section to view its content.</Typography>
      </Box>
    );
  }

  if (isPending && !isStreamingNarrative) {
    return <Spinner label="Generating narrative…" />;
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert
          severity="error"
          action={<Button size="small" onClick={() => generate({ collectionId, sectionName: sectionName || "" })}>Retry</Button>}
        >
          Failed to generate narrative.
        </Alert>
      </Box>
    );
  }

  const displayText = isStreamingNarrative ? streamingText : (narrative?.narrative || "");

  return (
    <Box sx={{ p: 3, maxWidth: 900 }}>
      {isStreamingNarrative && <LinearProgress sx={{ mb: 2, borderRadius: 1 }} />}
      <MarkdownRenderer content={displayText} />
      <div ref={bottomRef} />
    </Box>
  );
}
