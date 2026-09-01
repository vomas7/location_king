import { describe, expect, it } from "vitest";

import type { RoundResult, SessionView } from "~/api/types";
import { formats } from "~/domain/format";
import { ru as dictionary } from "~/i18n/ru";
import { buildShareText, roundMark } from "~/domain/share";

function result(score: number, distanceKm: string | null = "12.500"): RoundResult {
  return {
    id: score,
    index: 1,
    status: "guessed",
    view_extent_km: "5.000",
    target: [0, 0],
    guess: [1, 1],
    distance_km: distanceKm,
    score,
    max_score: 5000,
    accuracy: "50.00",
    country: null,
    guess_country: null,
    answer_seconds: null,
    zone: {
      id: 1,
      name: "Секретное место",
      description: null,
      category: "city",
      category_name: "Город",
      continent: "europe",
      continent_name: "Европа",
      country: null,
      region: null,
      tags: [],
      total_rounds: 0,
      average_distance: null,
    },
    guessed_at: null,
  };
}

const session: SessionView = {
  id: "s-1",
  status: "finished",
  challenge_day: null,
  rounds_total: 3,
  rounds_done: 3,
  total_score: 9000,
  average_score: 3000,
  time_limit_seconds: null,
  started_at: "2026-08-27T10:00:00Z",
  finished_at: "2026-08-27T10:10:00Z",
};

describe("roundMark", () => {
  it("разные результаты дают разные квадратики", () => {
    const marks = [5000, 4400, 3400, 2200, 500, 0].map((score) => roundMark(score, 5000));
    expect(new Set(marks).size).toBe(marks.length);
  });

  it("ноль очков — тёмный квадрат", () => {
    expect(roundMark(0, 5000)).toBe("⬛");
  });
});

describe("buildShareText", () => {
  it("собирает строку квадратиков и счёт", () => {
    const text = buildShareText({
      formats: formats("ru"),
      text: dictionary,
      session,
      results: [result(5000), result(2000), result(0)],
    });

    expect(text).toContain("Location King");
    expect(text).toContain("⭐");
    expect(text).toContain("⬛");
    expect(text).toContain("9 000 очков".replace(" ", " "));
  });

  it("не выдаёт места тем, кто ещё не играл", () => {
    const text = buildShareText({
      formats: formats("ru"),
      text: dictionary,
      session,
      results: [result(5000)],
    });

    expect(text).not.toContain("Секретное место");
    expect(text).not.toContain("0,");
  });

  it("отмечает челлендж отдельно", () => {
    const text = buildShareText({
      formats: formats("ru"),
      text: dictionary,
      session,
      results: [result(1000)],
      challengeDay: "2026-08-27",
    });

    expect(text).toContain("челлендж");
    expect(text).toContain("августа");
  });

  it("добавляет ссылку, если она передана", () => {
    const withLink = buildShareText({
      formats: formats("ru"),
      text: dictionary,
      session,
      results: [result(1000)],
      url: "https://example.com",
    });
    const withoutLink = buildShareText({
      formats: formats("ru"),
      text: dictionary,
      session,
      results: [result(1000)],
    });

    expect(withLink).toContain("https://example.com");
    expect(withoutLink).not.toContain("http");
  });

  it("показывает лучший раунд", () => {
    const text = buildShareText({
      formats: formats("ru"),
      text: dictionary,
      session,
      results: [result(1000, "48.200"), result(2000, "0.350")],
    });

    expect(text).toContain("Лучший раунд: 350 м");
  });

  it("переживает раунды без расстояния", () => {
    const text = buildShareText({
      formats: formats("ru"),
      text: dictionary,
      session,
      results: [result(0, null)],
    });
    expect(text).not.toContain("Лучший раунд");
  });
});
