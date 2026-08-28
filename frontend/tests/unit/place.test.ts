import { describe, expect, it } from "vitest";

import { placeFilter } from "~/domain/place";

describe("выбор места", () => {
  it("весь мир не ограничивает ничего", () => {
    expect(placeFilter(null)).toEqual({ continent: null, country_group: null });
  });

  it("часть света уходит в свой параметр", () => {
    expect(placeFilter("continent:europe")).toEqual({
      continent: "europe",
      country_group: null,
    });
  });

  it("страна уходит в свой параметр", () => {
    expect(placeFilter("country:eu")).toEqual({
      continent: null,
      country_group: "eu",
    });
  });

  it("два фильтра сразу не выставляются никогда", () => {
    for (const place of ["continent:asia", "country:russia", null]) {
      const filter = placeFilter(place);
      expect(filter.continent === null || filter.country_group === null).toBe(true);
    }
  });

  it("неизвестный ключ — ошибка, а не молчаливый пропуск фильтра", () => {
    expect(() => placeFilter("planet:mars")).toThrow(/Неизвестное место/);
  });
});
