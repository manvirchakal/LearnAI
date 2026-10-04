"use client";
import { Alert, Box, LinearProgress, Typography } from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import MarkdownRenderer from "@/components/shared/MarkdownRenderer";
import Button from "@/components/ui/Button";
import Spinner from "@/components/ui/Spinner";
import { useStudySession } from "./StudySession";

export default function NarrativePanel() {
  const { status, materials, streamingText, activity, error, generate } = useStudySession();

  if (status === "loading") return <Spinner label="Loading section…" />;

  if (status === "error" && !materials) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" action={<Button size="small" onClick={() => generate(false)}>Retry</Button>}>
          Couldn&apos;t generate this section: {error}
        </Alert>
      </Box>
    );
  }

  const streaming = status === "streaming";
  const text = streaming && streamingText ? streamingText : materials?.narrative ?? "";

  return (
    <Box sx={{ p: 3, maxWidth: 900 }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1, minHeight: 32 }}>
        <Typography variant="caption" color="text.secondary">{streaming ? activity : ""}</Typography>
        {!streaming && (
          <Button size="small" variant="text" startIcon={<RefreshIcon fontSize="small" />} onClick={() => generate(true)}>
            Regenerate
          </Button>
        )}
      </Box>
      {streaming && <LinearProgress sx={{ mb: 2, borderRadius: 1 }} />}
      {status === "error" && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {text ? (
        <MarkdownRenderer content={text} math={!streaming} />
      ) : (
        <Typography color="text.secondary" variant="body2">
          Personalizing this section to your learning profile…
        </Typography>
      )}
    </Box>
  );
}
