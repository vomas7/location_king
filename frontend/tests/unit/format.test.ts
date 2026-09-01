import { describe, expect, it } from "vitest";

import { formats, plural } from "~/domain/format";

const ru = formats("ru");
const en = formats("en");

describe("formatNumber", () => {
  it("разделяет разряды", () => {
    expect(ru.number(5000)).toMatch(/^5.000$/);
    expect(ru.number(12)).toBe("12");
  });

  it("округляет дробное", () => {
    expect(ru.number(1234.6)).toMatch(/^1.235$/);
  });
});

describe("formatDistance", () => {
  it("до километра показывает метры", () => {
    expect(ru.distance(0.35)).toBe("350 м");
    expect(ru.distance(0)).toBe("0 м");
  });

  it("до сотни километров показывает десятые", () => {
    expect(ru.distance(4.27)).toBe("4,3 км");
  });

  it("дальше округляет до километра", () => {
    expect(ru.distance(1234.5)).toMatch(/^1.235 км$/);
  });

  it("принимает строку — так расстояние приходит из API", () => {
    expect(ru.distance("12.500")).toBe("12,5 км");
  });

  it("на отсутствующем значении даёт прочерк", () => {
    expect(ru.distance(null)).toBe("—");
    expect(ru.distance("не число")).toBe("—");
  });
});

describe("formatExtent", () => {
  it("мелкие участки с десятыми, крупные целыми", () => {
    expect(ru.extent("4.312")).toBe("4,3 км");
    expect(ru.extent(61.7)).toBe("62 км");
  });
});

describe("formatPercent", () => {
  it("округляет до целого процента", () => {
    expect(ru.percent("87.44")).toBe("87%");
    expect(ru.percent(0)).toBe("0%");
  });

  it("на пустом значении даёт прочерк", () => {
    expect(ru.percent(null)).toBe("—");
  });
});

describe("formatDate", () => {
  it("выдаёт человеческую дату", () => {
    expect(ru.date("2026-08-27T10:00:00Z")).toContain("2026");
  });
});

describe("plural", () => {
  it.each([
    [1, "раунд"],
    [2, "раунда"],
    [4, "раунда"],
    [5, "раундов"],
    [11, "раундов"],
    [21, "раунд"],
    [112, "раундов"],
    [104, "раунда"],
  ])("для %i выбирает «%s»", (count, expected) => {
    expect(plural(count, "раунд", "раунда", "раундов")).toBe(expected);
  });
});

describe("formatTimeLimit", () => {
  it("без ограничения", () => {
    expect(ru.timeLimit(null)).toBe("Без лимита");
  });

  it("меньше минуты показывает секунды", () => {
    expect(ru.timeLimit(30)).toBe("30 сек");
  });

  it("от минуты показывает минуты", () => {
    expect(ru.timeLimit(60)).toBe("1 мин");
    expect(ru.timeLimit(120)).toBe("2 мин");
  });
});

describe("английский набор", () => {
  it("считает по-английски: точка в дробях и запятая в разрядах", () => {
    expect(en.distance(4.27)).toBe("4.3 km");
    expect(en.number(5000)).toBe("5,000");
    expect(en.distance(0.35)).toBe("350 m");
  });

  it("время на раунд называет по-английски", () => {
    expect(en.timeLimit(null)).toBe("No limit");
    expect(en.timeLimit(30)).toBe("30 s");
    expect(en.timeLimit(120)).toBe("2 min");
  });
});
