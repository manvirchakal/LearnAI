"use client";
import { DicesIcon, Gamepad2Icon } from "lucide-react";
import DynamicGameComponent from "@/components/game/DynamicGameComponent";
import { EmptyState, ErrorAlert, LoadingState } from "@/components/shared/States";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { errorMessage } from "@/api/client";
import { useRegenerateGame } from "@/api/study";
import { NotYet, useStudySession } from "./StudySession";

export default function GamePanel() {
  const { unit, status, materials, activity } = useStudySession();
  const regenerate = useRegenerateGame(unit);

  if (regenerate.isPending) return <LoadingState label="Designing a new game…" />;
  if (!materials) {
    if (status === "idle") return <NotYet />;
    return status === "error"
      ? <EmptyState icon={Gamepad2Icon} title="Game unavailable" />
      : <LoadingState label={activity ?? "Generating game…"} />;
  }

  const newGame = (
    <Button size="sm" variant="outline" onClick={() => regenerate.mutate()} disabled={status === "streaming"}>
      {status === "streaming" ? <Spinner /> : <DicesIcon />}
      New game
    </Button>
  );

  return (
    <div className="space-y-3 p-4">
      {regenerate.error && <ErrorAlert>{errorMessage(regenerate.error)}</ErrorAlert>}
      {materials.game_code ? (
        <>
          <div className="flex justify-end">{newGame}</div>
          <DynamicGameComponent key={materials.game_code} gameCode={materials.game_code} onRetry={() => regenerate.mutate()} />
        </>
      ) : (
        <EmptyState icon={Gamepad2Icon} title="No game yet" description="Generate one to practice what you just read.">
          {newGame}
        </EmptyState>
      )}
    </div>
  );
}
