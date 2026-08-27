/**
 * Текст, которым игрок делится после партии.
 *
 * Формат подсмотрен у Wordle: строка квадратиков читается без перехода по
 * ссылке и ничего не выдаёт тому, кто ещё не играл — в ней нет ни мест, ни
 * координат.
 */

import type { RoundResult, SessionView } from "~/api/types";
import { formatNumber } from "~/domain/format";
import { scoreRatio } from "~/domain/score";

/** Квадратик по доле набранных очков. */
const MARKS: { min: number; mark: string }[] = [
  { min: 0.98, mark: "⭐" },
  { min: 0.85, mark: "🟩" },
  { min: 0.6, mark: "🟨" },
  { min: 0.35, mark: "🟧" },
  { min: 0.01, mark: "🟥" },
  { min: 0, mark: "⬛" },
];

export function roundMark(score: number, maxScore: number): string {
  const ratio = scoreRatio(score, maxScore);
  return MARKS.find((entry) => ratio >= entry.min)?.mark ?? "⬛";
}

export interface ShareOptions {
  session: SessionView;
  results: RoundResult[];
  /** Заполнено, если это была партия челленджа. */
  challengeDay?: string;
  /** Адрес игры. Без него ссылка в текст не попадёт. */
  url?: string;
}

/** Собрать текст для отправки. */
export function buildShareText({ session, results, challengeDay, url }: ShareOptions): string {
  const title =
    challengeDay === undefined
      ? "Location King"
      : `Location King · челлендж ${new Date(challengeDay).toLocaleDateString("ru-RU", {
          day: "numeric",
          month: "long",
        })}`;

  const marks = results.map((result) => roundMark(result.score, result.max_score)).join("");
  const score = `${formatNumber(session.total_score)} очков`;

  const lines = [title, `${marks} ${score}`];

  const distances = results
    .map((result) => Number.parseFloat(result.distance_km ?? ""))
    .filter((value) => Number.isFinite(value));

  if (distances.length > 0) {
    const best = Math.min(...distances);
    lines.push(
      `Лучший раунд: ${best < 1 ? `${String(Math.round(best * 1000))} м` : `${best.toFixed(1)} км`}`,
    );
  }

  if (url !== undefined && url !== "") lines.push(url);

  return lines.join("\n");
}
