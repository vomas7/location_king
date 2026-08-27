import { describe, expect, it } from "vitest";

import {
  formatDate,
  formatDistance,
  formatExtent,
  formatNumber,
  formatPercent,
  plural,
} from "~/domain/format";

describe("formatNumber", () => {
  it("разделяет разряды", () => {
    expect(formatNumber(5000)).toMatch(/^5.000$/);
    expect(formatNumber(12)).toBe("12");
  });

  it("округляет дробное", () => {
    expect(formatNumber(1234.6)).toMatch(/^1.235$/);
  });
});

describe("formatDistance", () => {
  it("до километра показывает метры", () => {
    expect(formatDistance(0.35)).toBe("350 м");
    expect(formatDistance(0)).toBe("0 м");
  });

  it("до сотни километров показывает десятые", () => {
    expect(formatDistance(4.27)).toBe("4.3 км");
  });

  it("дальше округляет до километра", () => {
    expect(formatDistance(1234.5)).toMatch(/^1.235 км$/);
  });

  it("принимает строку — так расстояние приходит из API", () => {
    expect(formatDistance("12.500")).toBe("12.5 км");
  });

  it("на отсутствующем значении даёт прочерк", () => {
    expect(formatDistance(null)).toBe("—");
    expect(formatDistance("не число")).toBe("—");
  });
});

describe("formatExtent", () => {
  it("мелкие участки с десятыми, крупные целыми", () => {
    expect(formatExtent("4.312")).toBe("4.3 км");
    expect(formatExtent(61.7)).toBe("62 км");
  });
});

describe("formatPercent", () => {
  it("округляет до целого процента", () => {
    expect(formatPercent("87.44")).toBe("87%");
    expect(formatPercent(0)).toBe("0%");
  });

  it("на пустом значении даёт прочерк", () => {
    expect(formatPercent(null)).toBe("—");
  });
});

describe("formatDate", () => {
  it("выдаёт человеческую дату", () => {
    expect(formatDate("2026-08-27T10:00:00Z")).toContain("2026");
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
