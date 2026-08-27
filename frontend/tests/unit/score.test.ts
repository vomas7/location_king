import { describe, expect, it } from "vitest";

import { scoreRatio, scoreTier } from "~/domain/score";

describe("scoreRatio", () => {
  it("даёт долю от максимума", () => {
    expect(scoreRatio(2500, 5000)).toBe(0.5);
    expect(scoreRatio(5000, 5000)).toBe(1);
    expect(scoreRatio(0, 5000)).toBe(0);
  });

  it("не выходит за границы", () => {
    expect(scoreRatio(9000, 5000)).toBe(1);
    expect(scoreRatio(-10, 5000)).toBe(0);
  });

  it("на нулевом максимуме не делит на ноль", () => {
    expect(scoreRatio(100, 0)).toBe(0);
  });
});

describe("scoreTier", () => {
  it("точное попадание — высшая оценка", () => {
    expect(scoreTier(5000, 5000)).toEqual({ label: "В яблочко", tone: "perfect" });
  });

  it("ноль очков — низшая", () => {
    expect(scoreTier(0, 5000).tone).toBe("poor");
  });

  it("оценка не растёт с падением счёта", () => {
    const order = ["perfect", "great", "good", "fair", "poor"];
    const tones = [5000, 4400, 3500, 2000, 1000, 0].map((score) => scoreTier(score, 5000).tone);

    const positions = tones.map((tone) => order.indexOf(tone));
    expect(positions).toEqual([...positions].sort((a, b) => a - b));
  });
});
