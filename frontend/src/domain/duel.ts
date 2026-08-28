/**
 * Очередь дуэлей словами.
 *
 * Счётчик показывается в двух местах — на плитке режима и в самой панели, —
 * и в обоих должен считать одинаково: себя игрок в «ищущих соперника» не
 * числит.
 */

import { plural } from "~/domain/format";

/**
 * Сколько человек ищет соперника, кроме самого игрока.
 *
 * `mine` — стоит ли в очереди он сам: сервер считает всех, включая его.
 */
export function searchingText(searching: number, mine: boolean): string {
  if (searching === 0) return "Сейчас никто не ищет";

  const others = mine ? searching - 1 : searching;
  if (others === 0) return "Пока ищешь только ты";

  return `${String(others)} ${plural(others, "игрок ищет", "игрока ищут", "игроков ищут")} соперника`;
}
