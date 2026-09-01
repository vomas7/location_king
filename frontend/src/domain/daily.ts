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
import type { Formats } from "~/domain/format";
import type { Dictionary } from "~/i18n/dictionary";

export type DailyStage = "fresh" | "active" | "finished" | "lost";

export function dailyStage(session: SessionSummary | null): DailyStage {
  if (session === null) return "fresh";
  if (session.status === "finished") return "finished";
  if (session.status === "active") return "active";
  return "lost";
}

/** Что написать на плитке режима: ради чего в челлендж заходят сегодня. */
export function dailyStatus(
  daily: DailyChallenge | null,
  text: Dictionary,
  formats: Formats,
): string {
  if (daily === null) return text.daily.onceADay;

  switch (dailyStage(daily.my_session)) {
    case "finished":
      return text.daily.playedStatus(formats.number(daily.my_session?.total_score ?? 0));
    case "active":
      return text.daily.unfinishedStatus;
    case "lost":
      return text.daily.abandonedStatus;
    case "fresh":
      return daily.current_streak > 0
        ? text.daily.streakStatus(daily.current_streak)
        : text.daily.freshStatus;
  }
}

/** Плитка светится, только пока сегодня ещё можно что-то сделать. */
export function dailyAwaits(daily: DailyChallenge | null): boolean {
  if (daily === null) return false;

  const stage = dailyStage(daily.my_session);
  return stage === "fresh" || stage === "active";
}
