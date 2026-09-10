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
 * `bots` — сколько соперников-ботов свободно: пустая очередь тогда не тупик,
 * и говорить о ней как о тупике не за что.
 */
export function searchingText(
  searching: number,
  mine: boolean,
  text: Dictionary,
  bots = 0,
): string {
  const others = mine ? searching - 1 : searching;

  if (others === 0 && bots > 0) return text.duel.nobodyButBot;
  if (searching === 0) return text.duel.nobody;
  if (others === 0) return text.duel.onlyYou;

  return text.duel.searching(others);
}
