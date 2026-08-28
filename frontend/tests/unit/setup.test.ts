/** Условия партии: строка под кнопкой и параметры запроса. */

import { describe, expect, it } from "vitest";

import { DEFAULT_SETUP, describeSetup, levelHint, toOptions } from "~/domain/setup";

describe("describeSetup", () => {
  it("называет все пять условий подряд", () => {
    expect(describeSetup(DEFAULT_SETUP)).toBe(
      "5 раундов · Средне · 15 км · Весь мир · без лимита",
    );
  });

  it("склоняет раунды", () => {
    expect(describeSetup({ ...DEFAULT_SETUP, rounds: 3 })).toContain("3 раунда");
    expect(describeSetup({ ...DEFAULT_SETUP, rounds: 10 })).toContain("10 раундов");
  });

  it("называет выбранное место, а не ключ фильтра", () => {
    expect(describeSetup({ ...DEFAULT_SETUP, place: "continent:oceania" })).toContain("Океания");
    expect(describeSetup({ ...DEFAULT_SETUP, place: "country:eu" })).toContain("Евросоюз");
  });

  it("называет таймер", () => {
    expect(describeSetup({ ...DEFAULT_SETUP, timeLimit: 30 })).toContain("30 сек");
  });
});

describe("toOptions", () => {
  it("разбирает место в два фильтра сервера", () => {
    expect(toOptions({ ...DEFAULT_SETUP, place: "continent:europe" })).toEqual({
      rounds_total: 5,
      view_extent_km: 15,
      difficulty: "normal",
      continent: "europe",
      country_group: null,
      time_limit_seconds: null,
    });
  });

  it("весь мир не ограничивает ничем", () => {
    const options = toOptions(DEFAULT_SETUP);

    expect(options.continent).toBeNull();
    expect(options.country_group).toBeNull();
  });
});

describe("levelHint", () => {
  it("объясняет каждый уровень", () => {
    expect(levelHint("hardcore")).toContain("Дикая природа");
  });

  it("молчит про уровень, которого нет в списке", () => {
    expect(levelHint("nightmare")).toBe("");
  });
});
