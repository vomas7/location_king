/**
 * Очередь дуэлей словами.
 *
 * Счётчик показывается в двух местах — на плитке режима и в самой панели, —
 * и в обоих должен считать одинаково: себя игрок в «ищущих соперника» не
 * числит.
 */

import type { Dictionary } from "~/i18n/dictionary";

/**
 * Сколько человек ищет соперника, кроме самого игрока.
 *
 * `mine` — стоит ли в очереди он сам: сервер считает всех, включая его.
 */
export function searchingText(searching: number, mine: boolean, text: Dictionary): string {
  if (searching === 0) return text.duel.nobody;

  const others = mine ? searching - 1 : searching;
  if (others === 0) return text.duel.onlyYou;

  return text.duel.searching(others);
}
