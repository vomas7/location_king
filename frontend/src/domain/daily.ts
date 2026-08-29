/**
 * Челлендж дня глазами игрока.
 *
 * Партия по челленджу бывает в трёх состояниях, и все три надо называть
 * по-разному. Начатая — её продолжают. Законченная — показывают результат.
 * Брошенная — а бросается она молча, когда игрок начал любую другую партию, —
 * означает, что сегодня челлендж уже не сыграть: попытка в сутки одна.
 * Раньше брошенная считалась начатой, и кнопка «Продолжить челлендж»
 * упиралась в отказ сервера.
 */

import type { DailyChallenge, SessionSummary } from "~/api/types";
import { formatNumber, plural } from "~/domain/format";

export type DailyStage = "fresh" | "active" | "finished" | "lost";

export function dailyStage(session: SessionSummary | null): DailyStage {
  if (session === null) return "fresh";
  if (session.status === "finished") return "finished";
  if (session.status === "active") return "active";
  return "lost";
}

/** Что написать на плитке режима: ради чего в челлендж заходят сегодня. */
export function dailyStatus(daily: DailyChallenge | null): string {
  if (daily === null) return "Одна попытка в сутки";

  switch (dailyStage(daily.my_session)) {
    case "finished":
      return `Сыгран · ${formatNumber(daily.my_session?.total_score ?? 0)}`;
    case "active":
      return "Партия не доиграна";
    case "lost":
      return "Партия брошена";
    case "fresh":
      return daily.current_streak > 0
        ? `Серия ${String(daily.current_streak)} ${plural(daily.current_streak, "день", "дня", "дней")} — не прерывай`
        : "Сегодня ещё не сыгран";
  }
}

/** Плитка светится, только пока сегодня ещё можно что-то сделать. */
export function dailyAwaits(daily: DailyChallenge | null): boolean {
  if (daily === null) return false;

  const stage = dailyStage(daily.my_session);
  return stage === "fresh" || stage === "active";
}
