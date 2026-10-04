"use client";
import { Alert, Box, Typography } from "@mui/material";
import CasinoIcon from "@mui/icons-material/Casino";
import DynamicGameComponent from "@/components/game/DynamicGameComponent";
import Button from "@/components/ui/Button";
import Spinner from "@/components/ui/Spinner";
import { errorMessage } from "@/api/client";
import { useRegenerateGame } from "@/api/study";
import { useStudySession } from "./StudySession";

export default function GamePanel() {
  const { fileId, sectionId, status, materials, activity } = useStudySession();
  const regenerate = useRegenerateGame(fileId, sectionId);

  if (regenerate.isPending) return <Spinner label="Designing a new game…" />;
  if (!materials) {
    return status === "error"
      ? <Box sx={{ p: 4, textAlign: "center" }}><Typography color="text.secondary">Game unavailable.</Typography></Box>
      : <Spinner label={activity ?? "Generating game…"} />;
  }

  const newGame = (
    <Button size="small" startIcon={<CasinoIcon fontSize="small" />} onClick={() => regenerate.mutate()}
      disabled={status === "streaming"}>
      New game
    </Button>
  );

  return (
    <Box sx={{ p: 2 }}>
      {regenerate.error && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage(regenerate.error)}</Alert>}
      {materials.game_code ? (
        <>
          <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>{newGame}</Box>
          <DynamicGameComponent key={materials.game_code} gameCode={materials.game_code} onRetry={() => regenerate.mutate()} />
        </>
      ) : (
        <Box sx={{ p: 2, textAlign: "center" }}>
          <Typography color="text.secondary" gutterBottom>No game was generated for this section.</Typography>
          {newGame}
        </Box>
      )}
    </Box>
  );
}
