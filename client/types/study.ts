export interface StudyMaterials {
  narrative: string;
  game_idea: string;
  /** Body of a `Game()` function component; see DynamicGameComponent */
  game_code: string;
  /** Mermaid sources */
  diagrams: string[];
  /** Bumped by every write to the game; error reports name the version that broke */
  game_version: number;
}

export interface GameResponse {
  game_code: string;
  game_version: number;
}

/** An error the game sandbox caught (public/sandbox/game-runtime.js) */
export interface GameErrorReport {
  error: string;
  /** Line in the game code, when the stack named one */
  line?: number;
  phase?: "compile" | "render" | "runtime" | "promise";
  stack?: string;
}

/** Content-graph node names, emitted as each finishes */
export type StudyStage =
  | "load_cached" | "rag" | "narrative" | "game_idea" | "game_code" | "diagrams" | "save";

export type StudyStreamEvent =
  | { event: "token"; data: string }
  | { event: "stage"; data: StudyStage }
  | { event: "done"; data: StudyMaterials }
  | { event: "error"; data: string };
