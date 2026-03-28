export type VARKCategory = "Visual" | "Auditory" | "ReadingWriting" | "Kinesthetic";

export interface ProfileAnswers {
  Visual?: Record<string, number>;
  Auditory?: Record<string, number>;
  ReadingWriting?: Record<string, number>;
  Kinesthetic?: Record<string, number>;
}

export interface LearningProfile {
  answers: ProfileAnswers;
  description: string;
}

export interface SaveProfileResponse {
  message: string;
  description: string;
}
