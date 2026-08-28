/** Кому и что показывать в первой партии. */

import { describe, expect, it } from "vitest";

import type { UserProfile } from "~/api/types";
import { coachStep, FIRST_GAME_SETUP, isNewPlayer } from "~/domain/onboarding";

function player(gamesPlayed: number): UserProfile {
  return {
    id: 1,
    username: "player",
    display_name: null,
    email: "player@example.com",
    total_score: 0,
    games_played: gamesPlayed,
    total_rounds: 0,
    best_score: 0,
    average_score: null,
    average_distance: null,
    rating: 1000,
    duels_played: 0,
    created_at: "2026-08-28T10:00:00Z",
  };
}

describe("isNewPlayer", () => {
  it("новичок — тот, у кого нет ни одной законченной партии", () => {
    expect(isNewPlayer(player(0))).toBe(true);
  });

  it("после первой партии подсказки больше не нужны", () => {
    expect(isNewPlayer(player(1))).toBe(false);
  });

  it("без профиля решать нечего", () => {
    expect(isNewPlayer(null)).toBe(false);
  });
});

describe("coachStep", () => {
  it("сначала объясняет, на что игрок смотрит", () => {
    expect(coachStep(false, false)).toBe("look");
  });

  it("после «понятно» зовёт на карту", () => {
    expect(coachStep(true, false)).toBe("map");
  });

  it("поставленная точка переводит к ответу", () => {
    expect(coachStep(true, true)).toBe("answer");
  });

  it("точка важнее непрочитанного первого шага: подсказка не отстаёт от игрока", () => {
    expect(coachStep(false, true)).toBe("answer");
  });
});

describe("FIRST_GAME_SETUP", () => {
  it("первая партия — известные города крупным планом и без таймера", () => {
    expect(FIRST_GAME_SETUP.level).toBe("easy");
    expect(FIRST_GAME_SETUP.timeLimit).toBeNull();
    expect(FIRST_GAME_SETUP.extent).toBeGreaterThan(15);
  });
});
