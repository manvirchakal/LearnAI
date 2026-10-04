"use client";
import { Alert, Box, Typography } from "@mui/material";
import CasinoIcon from "@mui/icons-material/Casino";
import DynamicGameComponent from "@/components/game/DynamicGameComponent";
import Button from "@/components/ui/Button";
import Spinner from "@/components/ui/Spinner";
import { errorMessage } from "@/api/client";
import { useRegenerateGame, useStudyMaterials } from "@/api/study";

interface Props {
  fileId: string;
  sectionId: string;
}

export default function GamePanel({ fileId, sectionId }: Props) {
  const { data, isPending, error } = useStudyMaterials(fileId, sectionId);
  const regenerate = useRegenerateGame(fileId, sectionId);

  if ((isPending && !error) || regenerate.isPending) {
    return <Spinner label={regenerate.isPending ? "Designing a new game…" : "Generating game…"} />;
  }

  const newGameButton = (
    <Button size="small" startIcon={<CasinoIcon fontSize="small" />} onClick={() => regenerate.mutate()} disabled={!data}>
      New game
    </Button>
  );

  return (
    <Box sx={{ p: 2 }}>
      {regenerate.error && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage(regenerate.error)}</Alert>}
      {data?.game_code ? (
        <>
          <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>{newGameButton}</Box>
          <DynamicGameComponent key={data.game_code} gameCode={data.game_code} onRetry={() => regenerate.mutate()} />
        </>
      ) : (
        <Box sx={{ p: 2, textAlign: "center" }}>
          <Typography color="text.secondary" gutterBottom>
            {data ? "No game was generated for this section." : "Study materials aren't available yet."}
          </Typography>
          {newGameButton}
        </Box>
      )}
    </Box>
  );
}
