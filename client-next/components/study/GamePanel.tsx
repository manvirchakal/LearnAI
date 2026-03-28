"use client";
import { Box, Typography, Alert } from "@mui/material";
import { useState } from "react";
import DynamicGameComponent from "@/components/game/DynamicGameComponent";
import Button from "@/components/ui/Button";
import Spinner from "@/components/ui/Spinner";
import { useStudyStore } from "@/store/studyStore";
import { useGenerateGameCode } from "@/api/content";

export default function GamePanel() {
  const { collectionId, sectionName, narrative } = useStudyStore();
  const [gameError, setGameError] = useState<string | null>(null);
  const { mutate: generateGame, data: gameData, isPending, error } = useGenerateGameCode();

  const gameCode = gameData?.game_code || narrative?.game_code || null;

  const handleGenerate = () => {
    if (!collectionId || !sectionName) return;
    setGameError(null);
    generateGame({ collection_id: collectionId, section_name: sectionName });
  };

  if (!collectionId) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <Typography color="text.secondary">Select a section to generate a game.</Typography>
      </Box>
    );
  }

  if (!gameCode && !isPending) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <Typography color="text.secondary" gutterBottom>
          No game has been generated for this section yet.
        </Typography>
        <Button variant="contained" onClick={handleGenerate} disabled={!narrative}>
          Generate Game
        </Button>
        {!narrative && (
          <Typography variant="caption" color="text.disabled" display="block" sx={{ mt: 1 }}>
            Generate a narrative first.
          </Typography>
        )}
        {error && <Alert severity="error" sx={{ mt: 2 }}>Failed to generate game.</Alert>}
      </Box>
    );
  }

  if (isPending) {
    return <Spinner label="Generating game…" />;
  }

  return (
    <Box sx={{ p: 2 }}>
      {gameError && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Game encountered an error. Try regenerating.
          <Button size="small" sx={{ ml: 1 }} onClick={handleGenerate}>Regenerate</Button>
        </Alert>
      )}
      <DynamicGameComponent gameCode={gameCode!} onError={setGameError} />
    </Box>
  );
}
