/**
 * Как результат раунда выглядит для игрока.
 *
 * Сами очки считает сервер — здесь только словесная оценка и доля шкалы для
 * полосок прогресса.
 */

export interface ScoreTier {
  /** Имя ступени: слово к нему лежит в словаре, оно переводится */
  name: "perfect" | "great" | "good" | "fair" | "poor" | "awful";
  /** Цвет ступени. Их пять: «мимо» и «совсем не туда» окрашены одинаково */
  tone: "perfect" | "great" | "good" | "fair" | "poor";
}

const TIERS: { min: number; tier: ScoreTier }[] = [
  { min: 0.98, tier: { name: "perfect", tone: "perfect" } },
  { min: 0.85, tier: { name: "great", tone: "great" } },
  { min: 0.6, tier: { name: "good", tone: "good" } },
  { min: 0.35, tier: { name: "fair", tone: "fair" } },
  { min: 0.1, tier: { name: "poor", tone: "poor" } },
  { min: 0, tier: { name: "awful", tone: "poor" } },
];

const FALLBACK: ScoreTier = { name: "awful", tone: "poor" };

/** Доля набранных очков от максимума, от нуля до единицы. */
export function scoreRatio(score: number, maxScore: number): number {
  if (maxScore <= 0) return 0;
  return Math.min(Math.max(score / maxScore, 0), 1);
}

export function scoreTier(score: number, maxScore: number): ScoreTier {
  const ratio = scoreRatio(score, maxScore);
  return TIERS.find((entry) => ratio >= entry.min)?.tier ?? FALLBACK;
}

/**
 * Сколько раундов по зоне должно быть сыграно, чтобы среднее что-то значило.
 *
 * По одному-двум раундам «обычно промахиваются на столько-то» — это чужой
 * единственный ответ, выданный за общее правило.
 */
export const ENOUGH_ROUNDS = 5;

/** Как игрок отыграл зону по сравнению с остальными. */
export interface ZoneStanding {
  averageKm: number;
  /** Промах игрока меньше среднего. */
  better: boolean;
}

/**
 * Сравнение промаха со средним по зоне.
 *
 * Пусто, когда сравнивать не с чем: зону играли слишком мало раз или игрок
 * так и не поставил точку.
 */
export function zoneStanding(
  distanceKm: number | null,
  totalRounds: number,
  averageDistanceKm: number | null,
): ZoneStanding | null {
  if (distanceKm === null || averageDistanceKm === null) return null;
  if (totalRounds < ENOUGH_ROUNDS) return null;

  return { averageKm: averageDistanceKm, better: distanceKm < averageDistanceKm };
}
