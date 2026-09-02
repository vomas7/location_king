/**
 * Ход знакомства с игрой.
 *
 * Сеть подменяется целиком: проверяется не API, а то, в каком состоянии
 * оказывается экран после каждого шага. Главное здесь — что раунды листаются
 * на месте: сервер про то, где гость сейчас, не знает.
 */

import { act, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { RoundResult, RoundView } from "~/api/types";

import { renderHookWithLanguage as renderHook } from "./withLanguage";

const rounds = vi.fn();
const guess = vi.fn();

vi.mock("~/api/endpoints", () => ({
  demo: {
    rounds: (...args: unknown[]): unknown => rounds(...args) as unknown,
    guess: (...args: unknown[]): unknown => guess(...args) as unknown,
  },
}));

const { useDemo } = await import("~/state/useDemo");

function round(index: number, mode = "choice"): RoundView {
  return {
    id: index,
    index,
    status: "active",
    choices: [],
    view_extent_km: "45.000",
    max_zoom: 4,
    tiles_url: `/api/demo/rounds/${String(index)}/tiles/{z}/{x}/{y}.jpg`,
    attribution: "Провайдер",
    created_at: "2026-09-02T10:00:00Z",
    answer_mode: mode,
    max_score: 5000,
    hint: null,
    hint_cost: 0,
    deadline_at: null,
  };
}

function result(index: number, score: number): RoundResult {
  return {
    id: index,
    index,
    status: "guessed",
    view_extent_km: "45.000",
    target: [37.6, 55.7],
    guess: null,
    distance_km: "0.000",
    score,
    max_score: 5000,
    accuracy: null,
    country: "Россия",
    guess_country: "Россия",
    answer_seconds: null,
    zone: {
      id: 1,
      name: "Москва, центр",
      description: null,
      category: "city",
      category_name: "Город",
      continent: "europe",
      continent_name: "Европа",
      country: "Россия",
      region: "Москва",
      tags: [],
      total_rounds: 0,
      average_distance: null,
    },
    guessed_at: "2026-09-02T10:01:00Z",
  };
}

const THREE = [round(1), round(2, "country"), round(3, "point")];

async function started() {
  rounds.mockResolvedValue({ rounds: THREE });
  const view = renderHook(() => useDemo());

  await act(async () => {
    await view.result.current.start();
  });

  return view;
}

beforeEach(() => {
  rounds.mockReset();
  guess.mockReset();
});

describe("useDemo", () => {
  it("до начала показывать нечего", () => {
    const { result: view } = renderHook(() => useDemo());

    expect(view.current.state.phase).toBe("idle");
    expect(view.current.round).toBeNull();
  });

  it("раунды приезжают одним запросом", async () => {
    const { result: view } = await started();

    expect(rounds).toHaveBeenCalledTimes(1);
    expect(view.current.state.phase).toBe("playing");
    expect(view.current.state.rounds).toHaveLength(3);
    expect(view.current.round?.index).toBe(1);
  });

  it("отвечает по номеру текущего раунда", async () => {
    const { result: view } = await started();
    guess.mockResolvedValue(result(1, 5000));

    act(() => {
      view.current.pick({ kind: "country", code: "RUS", name: "Россия" });
    });
    await act(async () => {
      await view.current.submit();
    });

    expect(guess).toHaveBeenCalledWith(1, { kind: "country", code: "RUS", name: "Россия" });
    expect(view.current.state.phase).toBe("result");
    expect(view.current.state.lastResult?.score).toBe(5000);
  });

  it("без ответа сервер не тревожится", async () => {
    const { result: view } = await started();

    await act(async () => {
      await view.current.submit();
    });

    expect(guess).not.toHaveBeenCalled();
  });

  it("следующий раунд листается на месте, без запроса", async () => {
    const { result: view } = await started();
    guess.mockResolvedValue(result(1, 4000));

    act(() => {
      view.current.pick({ kind: "country", code: "RUS", name: "Россия" });
    });
    await act(async () => {
      await view.current.submit();
    });
    act(() => {
      view.current.advance();
    });

    expect(rounds).toHaveBeenCalledTimes(1);
    expect(view.current.round?.index).toBe(2);
    expect(view.current.round?.answer_mode).toBe("country");
    // Ответ прошлого раунда не переезжает в следующий
    expect(view.current.state.guess).toBeNull();
  });

  it("после последнего раунда зовёт заводить учётную запись", async () => {
    const { result: view } = await started();

    for (const [index, score] of [
      [1, 5000],
      [2, 3000],
      [3, 1000],
    ] as const) {
      guess.mockResolvedValue(result(index, score));

      act(() => {
        view.current.pick({ kind: "country", code: "RUS", name: "Россия" });
      });
      await act(async () => {
        await view.current.submit();
      });
      act(() => {
        view.current.advance();
      });
    }

    expect(view.current.state.phase).toBe("finished");
    expect(view.current.totalScore).toBe(9000);
    expect(view.current.state.results).toHaveLength(3);
  });

  it("последний раунд знает, что он последний", async () => {
    const { result: view } = await started();

    expect(view.current.isLastRound).toBe(false);

    act(() => {
      view.current.pick({ kind: "country", code: "RUS", name: "Россия" });
    });
    guess.mockResolvedValue(result(1, 100));
    await act(async () => {
      await view.current.submit();
    });
    act(() => {
      view.current.advance();
    });
    act(() => {
      view.current.pick({ kind: "country", code: "RUS", name: "Россия" });
    });
    guess.mockResolvedValue(result(2, 100));
    await act(async () => {
      await view.current.submit();
    });
    act(() => {
      view.current.advance();
    });

    expect(view.current.isLastRound).toBe(true);
  });

  it("отказ сервера показывается, а знакомство не рушится", async () => {
    rounds.mockRejectedValue(new Error("нет сети"));
    const { result: view } = renderHook(() => useDemo());

    await act(async () => {
      await view.current.start();
    });

    await waitFor(() => {
      expect(view.current.state.error).not.toBeNull();
    });
    expect(view.current.state.phase).toBe("idle");
  });

  it("пройти заново — это тот же запрос с начала", async () => {
    const { result: view } = await started();
    guess.mockResolvedValue(result(1, 5000));

    act(() => {
      view.current.pick({ kind: "country", code: "RUS", name: "Россия" });
    });
    await act(async () => {
      await view.current.submit();
    });

    await act(async () => {
      await view.current.start();
    });

    expect(rounds).toHaveBeenCalledTimes(2);
    expect(view.current.round?.index).toBe(1);
    expect(view.current.state.results).toHaveLength(0);
    expect(view.current.totalScore).toBe(0);
  });
});
