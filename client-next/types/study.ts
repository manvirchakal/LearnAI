export interface StudyMaterials {
  narrative: string;
  game_idea: string;
  /** Body of a `Game()` function component; see DynamicGameComponent */
  game_code: string;
  /** Mermaid sources */
  diagrams: string[];
}

export interface GameResponse {
  game_code: string;
}

/** Content-graph node names, emitted as each finishes */
export type StudyStage =
  | "load_cached" | "rag" | "narrative" | "game_idea" | "game_code" | "validate_code" | "diagrams" | "save";

export type StudyStreamEvent =
  | { event: "token"; data: string }
  | { event: "stage"; data: StudyStage }
  | { event: "done"; data: StudyMaterials }
  | { event: "error"; data: string };
