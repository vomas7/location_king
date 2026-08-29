/**
 * Меню, пережившее партию.
 *
 * Проверяется разбор сохранённого: в хранилище может лежать что угодно, и
 * ни одно из этого не должно превратиться в условия, с которыми партия не
 * начнётся.
 */

import { describe, expect, it } from "vitest";

import type { MenuState } from "~/domain/menu";
import { defaultMenu, parseMenu } from "~/domain/menu";
import { DEFAULT_SETUP } from "~/domain/setup";

const FALLBACK: MenuState = defaultMenu(DEFAULT_SETUP);

function stored(value: unknown): MenuState {
  return parseMenu(JSON.stringify(value), FALLBACK);
}

describe("разбор сохранённого меню", () => {
  it("пустое хранилище даёт меню по умолчанию", () => {
    expect(parseMenu(null, FALLBACK)).toEqual(FALLBACK);
  });

  it("не JSON не роняет разбор", () => {
    expect(parseMenu("{не json", FALLBACK)).toEqual(FALLBACK);
  });

  it("возвращает то, что сохранили", () => {
    const chosen: MenuState = {
      setup: { ...DEFAULT_SETUP, rounds: 10, level: "hardcore", place: "continent:asia" },
      mode: "room",
      section: "board",
    };

    expect(stored(chosen)).toEqual(chosen);
  });

  it("вариант, которого больше нет, заменяется значением по умолчанию", () => {
    const parsed = stored({
      setup: { ...DEFAULT_SETUP, level: "невиданный", place: "continent:atlantis", rounds: 7 },
      mode: "solo",
      section: "profile",
    });

    expect(parsed.setup.level).toBe(DEFAULT_SETUP.level);
    expect(parsed.setup.place).toBe(DEFAULT_SETUP.place);
    expect(parsed.setup.rounds).toBe(DEFAULT_SETUP.rounds);
  });

  it("незнакомые режим и раздел заменяются значением по умолчанию", () => {
    const parsed = stored({ setup: DEFAULT_SETUP, mode: "турнир", section: "достижения" });

    expect(parsed.mode).toBe(FALLBACK.mode);
    expect(parsed.section).toBe(FALLBACK.section);
  });

  it("«без лимита» — это выбор, а не отсутствие значения", () => {
    const parsed = stored({
      setup: { ...DEFAULT_SETUP, timeLimit: null },
      mode: "solo",
      section: "profile",
    });

    expect(parsed.setup.timeLimit).toBeNull();
  });

  it("огрызок вместо условий не ломает остальное", () => {
    const parsed = parseMenu('{"setup":"хардкор","mode":"duel"}', FALLBACK);

    expect(parsed.setup).toEqual(DEFAULT_SETUP);
    expect(parsed.mode).toBe("duel");
  });
});
