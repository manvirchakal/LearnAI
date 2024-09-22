export const calculateLearningProfile = (answers) => {
    const categories = Object.keys(answers);
    const scores = {};

    categories.forEach(category => {
      const categoryScores = Object.values(answers[category]);
      const totalScore = categoryScores.reduce((sum, score) => sum + parseInt(score), 0);
      scores[category] = totalScore / categoryScores.length;
    });

    return scores;
};