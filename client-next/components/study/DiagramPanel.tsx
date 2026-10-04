"use client";
import { Box, Typography } from "@mui/material";
import MermaidDiagram from "@/components/shared/MermaidDiagram";
import Spinner from "@/components/ui/Spinner";
import { useStudyMaterials } from "@/api/study";

interface Props {
  fileId: string;
  sectionId: string;
}

export default function DiagramPanel({ fileId, sectionId }: Props) {
  const { data, isPending, error } = useStudyMaterials(fileId, sectionId);

  if (isPending && !error) return <Spinner label="Generating diagrams…" />;
  const diagrams = data?.diagrams ?? [];

  if (diagrams.length === 0) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <Typography color="text.secondary">No diagrams for this section.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 3 }}>
      {diagrams.map((diagram, i) => (
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
