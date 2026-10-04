export type VARKCategory = "Visual" | "Auditory" | "ReadingWriting" | "Kinesthetic";

/** Agreement with each statement, 1 (strongly disagree) to 5 (strongly agree) */
export type ProfileAnswers = Record<VARKCategory, Record<string, number>>;

export interface Questionnaire {
  scale: { min: number; max: number };
  categories: Record<VARKCategory, string[]>;
}

export interface LearningProfile {
  answers: ProfileAnswers;
  description: string;
}
