/**
 * Что показать игроку, который ещё не играл.
 *
 * Снимок без подписей и карта мира выглядят понятно ровно до момента, когда
 * надо что-то сделать. Отдельного признака «прошёл обучение» для этого не
 * нужно: сервер и так знает, сколько партий сыграно, и первая партия — это
 * та, перед которой их ноль.
 */

import type { UserProfile } from "~/api/types";

/** Ещё ни одной законченной партии. */
export function isNewPlayer(user: UserProfile | null): boolean {
  return user !== null && user.games_played === 0;
}

/**
 * Настройки первой партии.
 *
 * Она должна быть узнаваемой, а не честной: человек, который первым же
 * раундом получил пустыню в кадре шириной пятнадцать километров, второй
 * партии не начинает. Дальше он выставит всё сам.
 */
export const FIRST_GAME_SETUP = {
  rounds: 5,
  extent: 40,
  level: "easy",
  timeLimit: null,
} as const;

/** Шаг подсказки в первом раунде. */
export type CoachStep = "look" | "map" | "answer";

/**
 * Какой шаг показывать. Выводится из того, что игрок уже сделал, а не из
 * счётчика нажатий: подсказка, которая висит после выполненного действия,
 * раздражает сильнее, чем её отсутствие.
 */
export function coachStep(acknowledged: boolean, hasGuess: boolean): CoachStep {
  if (hasGuess) return "answer";
  return acknowledged ? "map" : "look";
}
