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
