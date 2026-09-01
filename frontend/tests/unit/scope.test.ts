import { describe, expect, it } from "vitest";

import type { StartSessionOptions } from "~/api/types";
import { scopeLabel, scopeQuery } from "~/domain/scope";

function options(overrides: Partial<StartSessionOptions> = {}): StartSessionOptions {
  return {
    rounds_total: 5,
    difficulty: "normal",
    answer_mode: "point",
    continent: null,
    country_group: null,
    time_limit_seconds: null,
    ...overrides,
  };
}

describe("зачёт по условиям партии", () => {
  it("уровень уходит в запрос всегда", () => {
    expect(scopeQuery(options({ difficulty: "hardcore" }))).toBe("difficulty=hardcore");
  });

  it("страна добавляется к уровню", () => {
    const query = scopeQuery(options({ difficulty: "easy", country_group: "russia" }));

    expect(query).toBe("difficulty=easy&country_group=russia");
  });

  it("подпись читается человеком", () => {
    expect(scopeLabel(options({ difficulty: "hardcore", country_group: "usa" }))).toBe(
      "Хардкор · США",
    );
    expect(scopeLabel(options({ difficulty: "normal", continent: "africa" }))).toBe(
      "Средне · Африка",
    );
  });

  it("запрос и подпись описывают одно и то же", () => {
    const chosen = options({ difficulty: "hard", continent: "asia" });

    expect(scopeQuery(chosen).split("&")).toHaveLength(2);
    expect(scopeLabel(chosen).split(" · ")).toHaveLength(2);
  });

  it("неизвестное значение показывается как есть, а не теряется", () => {
    expect(scopeLabel(options({ difficulty: "невиданный" }))).toBe("невиданный");
  });
});
