"use client";
import { DicesIcon, Gamepad2Icon } from "lucide-react";
import { useRef } from "react";
import DynamicGameComponent from "@/components/game/DynamicGameComponent";
import { EmptyState, ErrorAlert, LoadingState } from "@/components/shared/States";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { errorMessage } from "@/api/client";
import { useFixGame, useRegenerateGame } from "@/api/study";
import type { GameErrorReport } from "@/types/study";
import { NotYet, useStudySession } from "./StudySession";

/** Fixes sent without asking, in a row; after that the student decides */
const MAX_AUTO_FIXES = 3;

export default function GamePanel() {
  const { unit, status, materials, activity } = useStudySession();
  const regenerate = useRegenerateGame(unit);
  const fix = useFixGame(unit);
  const autoFixes = useRef(0);
  const lastError = useRef<GameErrorReport | null>(null);

  if (regenerate.isPending) return <LoadingState label="Designing a new game…" />;
  if (!materials) {
    if (status === "idle") return <NotYet />;
    return status === "error"
      ? <EmptyState icon={Gamepad2Icon} title="Game unavailable" />
      : <LoadingState label={activity ?? "Generating game…"} />;
  }

  const sendFix = (report: GameErrorReport) => fix.mutate({ ...report, version: materials.game_version ?? 0 });

  const onGameError = (report: GameErrorReport) => {
    lastError.current = report;
    if (fix.isPending || autoFixes.current >= MAX_AUTO_FIXES) return;
    autoFixes.current += 1;
    sendFix(report);
  };

  const newGame = () => {
    autoFixes.current = 0;
    fix.reset();
    regenerate.mutate();
  };

  const newGameButton = (
    <Button size="sm" variant="outline" onClick={newGame} disabled={status === "streaming"}>
      {status === "streaming" ? <Spinner /> : <DicesIcon />}
      New game
    </Button>
  );

  return (
    <div className="space-y-3 p-4">
      {regenerate.error && <ErrorAlert>{errorMessage(regenerate.error)}</ErrorAlert>}
      {fix.error && <ErrorAlert title="Couldn't fix the game">{errorMessage(fix.error)}</ErrorAlert>}
      {materials.game_code ? (
        <>
          <div className="flex justify-end">{newGameButton}</div>
          <DynamicGameComponent
            key={`${materials.game_version ?? 0}:${materials.game_code}`}
            gameCode={materials.game_code}
            onGameError={onGameError}
            fixing={fix.isPending}
            onFix={() => lastError.current && sendFix(lastError.current)}
            onRetry={newGame}
          />
        </>
      ) : (
        <EmptyState icon={Gamepad2Icon} title="No game yet" description="Generate one to practice what you just read.">
          {newGameButton}
        </EmptyState>
      )}
    </div>
  );
}
