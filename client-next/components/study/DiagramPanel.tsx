"use client";
import { Box, Typography, Alert } from "@mui/material";
import MermaidDiagram from "@/components/shared/MermaidDiagram";
import Spinner from "@/components/ui/Spinner";
import { useStudyStore } from "@/store/studyStore";

export default function DiagramPanel() {
  const { narrative } = useStudyStore();

  if (!narrative) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <Typography color="text.secondary">Generate a narrative first to see diagrams.</Typography>
      </Box>
    );
  }

  const diagrams: string[] = narrative.diagrams || [];

  if (diagrams.length === 0) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <Typography color="text.secondary">No diagrams were generated for this section.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, display: "flex", flexDirection: "column", gap: 4 }}>
      {diagrams.map((diagram, i) => (
        <Box
          key={i}
          sx={{
            p: 2,
            bgcolor: "white",
            borderRadius: 2,
            border: "1px solid #e9ecef",
            boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
          }}
        >
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1, fontWeight: 600 }}>
            Diagram {i + 1}
          </Typography>
          <MermaidDiagram diagram={diagram} />
        </Box>
      ))}
    </Box>
  );
}
