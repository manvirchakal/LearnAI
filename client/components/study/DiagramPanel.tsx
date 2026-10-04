"use client";
import { Box, Typography } from "@mui/material";
import MermaidDiagram from "@/components/shared/MermaidDiagram";
import Spinner from "@/components/ui/Spinner";
import { NotYet, useStudySession } from "./StudySession";

export default function DiagramPanel() {
  const { status, materials, activity } = useStudySession();

  if (!materials) {
    if (status === "idle") return <NotYet />;
    return status === "error"
      ? <Box sx={{ p: 4, textAlign: "center" }}><Typography color="text.secondary">Diagrams unavailable.</Typography></Box>
      : <Spinner label={activity ?? "Generating diagrams…"} />;
  }

  if (materials.diagrams.length === 0) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <Typography color="text.secondary">No diagrams were generated.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 3 }}>
      {materials.diagrams.map((diagram, i) => (
        <Box key={i} sx={{ p: 2, bgcolor: "white", borderRadius: 2, border: "1px solid #e9ecef", overflowX: "auto" }}>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1, fontWeight: 600 }}>
            Diagram {i + 1}
          </Typography>
          <MermaidDiagram diagram={diagram} />
        </Box>
      ))}
    </Box>
  );
}
