"use client";
import { Alert, Box, LinearProgress, Typography } from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import MarkdownRenderer from "@/components/shared/MarkdownRenderer";
import Button from "@/components/ui/Button";
import { errorMessage } from "@/api/client";
import { useRegenerateStudy, useStudyMaterials } from "@/api/study";

interface Props {
  fileId: string;
  sectionId: string;
}

export default function NarrativePanel({ fileId, sectionId }: Props) {
  const { data, isPending, error, refetch, isFetching } = useStudyMaterials(fileId, sectionId);
  const regenerate = useRegenerateStudy(fileId, sectionId);
  const busy = isFetching || regenerate.isPending;

  if (isPending && !error) {
    return (
      <Box sx={{ p: 4 }}>
        <LinearProgress sx={{ mb: 2, borderRadius: 1 }} />
        <Typography color="text.secondary" variant="body2">
          Personalizing this section to your learning profile… the first visit can take a minute.
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert
          severity="error"
          action={<Button size="small" onClick={() => refetch()} loading={isFetching}>Retry</Button>}
        >
          Couldn&apos;t generate this section: {errorMessage(error)}
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, maxWidth: 900 }}>
      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>
        <Button
          size="small"
          variant="text"
          startIcon={<RefreshIcon fontSize="small" />}
          loading={regenerate.isPending}
          disabled={busy}
          onClick={() => regenerate.mutate()}
        >
          Regenerate
        </Button>
      </Box>
      {regenerate.error && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage(regenerate.error)}</Alert>}
      {busy && <LinearProgress sx={{ mb: 2, borderRadius: 1 }} />}
      <MarkdownRenderer content={data?.narrative ?? ""} />
    </Box>
  );
}
