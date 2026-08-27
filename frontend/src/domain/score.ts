/**
 * Как результат раунда выглядит для игрока.
 *
 * Сами очки считает сервер — здесь только словесная оценка и доля шкалы для
 * полосок прогресса.
 */

export interface ScoreTier {
  label: string;
  tone: "perfect" | "great" | "good" | "fair" | "poor";
}

const TIERS: { min: number; tier: ScoreTier }[] = [
  { min: 0.98, tier: { label: "В яблочко", tone: "perfect" } },
  { min: 0.85, tier: { label: "Отлично", tone: "great" } },
  { min: 0.6, tier: { label: "Хорошо", tone: "good" } },
  { min: 0.35, tier: { label: "Неплохо", tone: "fair" } },
  { min: 0.1, tier: { label: "Мимо", tone: "poor" } },
  { min: 0, tier: { label: "Совсем не туда", tone: "poor" } },
];

const FALLBACK: ScoreTier = { label: "Совсем не туда", tone: "poor" };

/** Доля набранных очков от максимума, от нуля до единицы. */
export function scoreRatio(score: number, maxScore: number): number {
  if (maxScore <= 0) return 0;
  return Math.min(Math.max(score / maxScore, 0), 1);
}

export function scoreTier(score: number, maxScore: number): ScoreTier {
  const ratio = scoreRatio(score, maxScore);
  return TIERS.find((entry) => ratio >= entry.min)?.tier ?? FALLBACK;
}
