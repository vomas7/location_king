/**
 * Челлендж дня глазами игрока.
 *
 * Брошенная партия — отдельное состояние, а не «начатая»: попытка в сутки
 * одна, и кнопка «Продолжить» на брошенной упиралась в отказ сервера.
 */

import { describe, expect, it } from "vitest";

import type { DailyChallenge, SessionSummary } from "~/api/types";
import { dailyAwaits, dailyStage, dailyStatus } from "~/domain/daily";
import { formats } from "~/domain/format";

const ru = formats("ru");

function session(status: string, total_score = 0): SessionSummary {
  return {
    id: "s-1",
    status,
    challenge_day: "2026-08-29",
    rounds_total: 5,
    rounds_done: 2,
    total_score,
    started_at: "2026-08-29T10:00:00Z",
    finished_at: null,
  };
}

function challenge(my_session: SessionSummary | null, current_streak = 0): DailyChallenge {
  return {
    day: "2026-08-29",
    rounds_total: 5,
    view_extent_km: 15,
    my_session,
    finished_players: 3,
    current_streak,
    best_streak: current_streak,
    results: [],
  };
}

describe("состояние челленджа", () => {
  it("партии не было", () => {
    expect(dailyStage(null)).toBe("fresh");
  });

  it("начатая продолжается", () => {
    expect(dailyStage(session("active"))).toBe("active");
  });

  it("законченная показывает результат", () => {
    expect(dailyStage(session("finished"))).toBe("finished");
  });

  it("брошенная — не начатая", () => {
    expect(dailyStage(session("abandoned"))).toBe("lost");
  });
});

describe("подпись на плитке", () => {
  it("без ответа сервера говорит про правило", () => {
    expect(dailyStatus(null, ru)).toBe("Одна попытка в сутки");
  });

  it("законченная называет счёт", () => {
    expect(dailyStatus(challenge(session("finished", 12500)), ru)).toContain("12");
  });

  it("брошенная и начатая называются по-разному", () => {
    expect(dailyStatus(challenge(session("abandoned")), ru)).not.toBe(
      dailyStatus(challenge(session("active")), ru),
    );
  });

  it("серия дней зовёт вернуться", () => {
    expect(dailyStatus(challenge(null, 3), ru)).toContain("3");
  });
});

describe("плитка светится, пока сегодня есть что сделать", () => {
  it("не сыгран — светится", () => {
    expect(dailyAwaits(challenge(null))).toBe(true);
  });

  it("не доигран — светится", () => {
    expect(dailyAwaits(challenge(session("active")))).toBe(true);
  });

  it("сыгран — гаснет", () => {
    expect(dailyAwaits(challenge(session("finished")))).toBe(false);
  });

  it("брошен — гаснет: сегодня уже ничего не сделать", () => {
    expect(dailyAwaits(challenge(session("abandoned")))).toBe(false);
  });
});
