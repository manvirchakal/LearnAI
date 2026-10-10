export type VARKCategory = "Visual" | "Auditory" | "ReadingWriting" | "Kinesthetic";

export function calculateVARKScores(
  answers: Record<string, Record<string, number>>
): Record<VARKCategory, number> {
  const categories: VARKCategory[] = ["Visual", "Auditory", "ReadingWriting", "Kinesthetic"];
  const scores = {} as Record<VARKCategory, number>;

  for (const cat of categories) {
    const categoryAnswers = answers[cat] ?? {};
    const values = Object.values(categoryAnswers);
    scores[cat] = values.length > 0
      ? values.reduce((sum, v) => sum + v, 0) / values.length
      : 0;
  }

  return scores;
}

export function getDominantStyle(scores: Record<VARKCategory, number>): VARKCategory {
  return Object.entries(scores).reduce(
    (best, [cat, score]) => (score > best[1] ? [cat, score] : best),
    ["Visual", 0] as [string, number]
  )[0] as VARKCategory;
}
