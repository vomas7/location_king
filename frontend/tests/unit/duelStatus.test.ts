/**
 * Очередь дуэлей словами.
 *
 * Одна и та же строка стоит на плитке режима и в панели, поэтому считает она
 * тоже одинаково: себя игрок в «ищущих соперника» не числит. Пустая очередь
 * при этом перестала быть тупиком — с ботом сыграть можно, — и говорить о ней
 * как о тупике больше нельзя.
 */

import { describe, expect, it } from "vitest";

import { searchingText } from "~/domain/duel";
import { ru } from "~/i18n/ru";

describe("searchingText", () => {
  it("пустая очередь без ботов — так и говорит", () => {
    expect(searchingText(0, false, ru)).toBe(ru.duel.nobody);
  });

  it("сам в очереди и больше никого", () => {
    expect(searchingText(1, true, ru)).toBe(ru.duel.onlyYou);
  });

  it("себя в чужих не считает", () => {
    expect(searchingText(3, true, ru)).toBe(ru.duel.searching(2));
    expect(searchingText(3, false, ru)).toBe(ru.duel.searching(3));
  });

  it("никто не ищет, но есть бот — это не тупик", () => {
    expect(searchingText(0, false, ru, 5)).toBe(ru.duel.nobodyButBot);
    expect(searchingText(1, true, ru, 5)).toBe(ru.duel.nobodyButBot);
  });

  it("живой соперник важнее бота: про него и говорим", () => {
    expect(searchingText(2, false, ru, 5)).toBe(ru.duel.searching(2));
  });
});
