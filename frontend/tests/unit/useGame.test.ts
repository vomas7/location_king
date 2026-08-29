/**
 * Тесты хода партии.
 *
 * Сеть подменяется целиком: проверяется не API, а то, в каком состоянии
 * оказывается экран после каждого шага.
 */

import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { GuessResponse, RoundResult, RoundView, SessionState, SessionView } from "~/api/types";

const start = vi.fn();
const guess = vi.fn();
const finish = vi.fn();
const hint = vi.fn();

vi.mock("~/api/endpoints", () => ({
  game: {
    start: (...args: unknown[]): unknown => start(...args) as unknown,
    guess: (...args: unknown[]): unknown => guess(...args) as unknown,
    finish: (...args: unknown[]): unknown => finish(...args) as unknown,
    hint: (...args: unknown[]): unknown => hint(...args) as unknown,
  },
}));

const { useGame } = await import("~/state/useGame");

function round(index: number, overrides: Partial<RoundView> = {}): RoundView {
  return {
    id: index,
    index,
    status: "active",
    view_extent_km: "5.000",
    max_zoom: 4,
    tiles_url: `/api/rounds/${String(index)}/tiles/{z}/{x}/{y}.jpg`,
    attribution: "Провайдер",
    created_at: "2026-08-27T10:00:00Z",
    answer_mode: "point",
    max_score: 5000,
    hint: null,
    hint_cost: 1500,
    deadline_at: null,
    ...overrides,
  };
}

function session(overrides: Partial<SessionView> = {}): SessionView {
  return {
    id: "s-1",
    status: "active",
    challenge_day: null,
    rounds_total: 2,
    rounds_done: 0,
    total_score: 0,
    average_score: null,
    time_limit_seconds: null,
    started_at: "2026-08-27T10:00:00Z",
    finished_at: null,
    ...overrides,
  };
}

function result(index: number, score: number): RoundResult {
  return {
    id: index,
    index,
    status: "guessed",
    view_extent_km: "5.000",
    target: [37.6, 55.7],
    guess: [30.0, 50.0],
    distance_km: "812.500",
    score,
    max_score: 5000,
    accuracy: "12.00",
    country: null,
    guess_country: null,
    answer_seconds: "8.40",
    zone: {
      id: 1,
      name: "Тестовая зона",
      description: null,
      category: "city",
      category_name: "Город",
      continent: "europe",
      continent_name: "Европа",
      country: "Россия",
      region: null,
      tags: [],
      total_rounds: 0,
      average_distance: null,
    },
    guessed_at: "2026-08-27T10:01:00Z",
  };
}

const OPTIONS = {
  rounds_total: 2,
  view_extent_km: 5,
  continent: null,
  country_group: null,
  difficulty: "normal",
  answer_mode: "point",
  time_limit_seconds: null,
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useGame", () => {
  it("начинает без партии", () => {
    const { result: hook } = renderHook(() => useGame(vi.fn()));

    expect(hook.current.state.phase).toBe("idle");
    expect(hook.current.state.session).toBeNull();
  });

  it("после старта открывает первый раунд", async () => {
    const opened: SessionState = { session: session(), current_round: round(1), results: [] };
    start.mockResolvedValue(opened);

    const { result: hook } = renderHook(() => useGame(vi.fn()));
    await act(async () => {
      await hook.current.start(OPTIONS);
    });

    expect(hook.current.state.phase).toBe("playing");
    expect(hook.current.state.round?.index).toBe(1);
    expect(hook.current.state.guess).toBeNull();
  });

  it("сообщает об ошибке старта, не ломая состояние", async () => {
    const { ApiError } = await import("~/api/client");
    start.mockRejectedValue(new ApiError(404, "Нет активных зон"));

    const { result: hook } = renderHook(() => useGame(vi.fn()));
    await act(async () => {
      await hook.current.start(OPTIONS).catch(() => undefined);
    });

    expect(hook.current.state.phase).toBe("idle");
    expect(hook.current.state.error).toBe("Нет активных зон");
  });

  it("запоминает поставленную точку", async () => {
    start.mockResolvedValue({ session: session(), current_round: round(1), results: [] });

    const { result: hook } = renderHook(() => useGame(vi.fn()));
    await act(async () => {
      await hook.current.start(OPTIONS);
    });

    act(() => {
      hook.current.pick({ kind: "point", longitude: 30, latitude: 50 });
    });

    expect(hook.current.state.guess).toEqual({ kind: "point", longitude: 30, latitude: 50 });
  });

  it("после догадки показывает результат и держит следующий раунд наготове", async () => {
    start.mockResolvedValue({ session: session(), current_round: round(1), results: [] });
    const answer: GuessResponse = {
      result: result(1, 1200),
      session: session({ rounds_done: 1, total_score: 1200 }),
      next_round: round(2),
      is_session_finished: false,
    };
    guess.mockResolvedValue(answer);

    const onEnd = vi.fn();
    const { result: hook } = renderHook(() => useGame(onEnd));
    await act(async () => {
      await hook.current.start(OPTIONS);
    });
    act(() => {
      hook.current.pick({ kind: "point", longitude: 30, latitude: 50 });
    });
    await act(async () => {
      await hook.current.submit();
    });

    expect(hook.current.state.phase).toBe("result");
    expect(hook.current.state.lastResult?.score).toBe(1200);
    expect(hook.current.state.results).toHaveLength(1);
    expect(onEnd).not.toHaveBeenCalled();

    act(() => {
      hook.current.advance();
    });
    expect(hook.current.state.phase).toBe("playing");
    expect(hook.current.state.round?.index).toBe(2);
    expect(hook.current.state.guess).toBeNull();
  });

  it("на последнем раунде завершает партию", async () => {
    start.mockResolvedValue({ session: session(), current_round: round(1), results: [] });
    guess.mockResolvedValue({
      result: result(1, 900),
      session: session({ status: "finished", rounds_done: 2, total_score: 900 }),
      next_round: null,
      is_session_finished: true,
    });

    const onEnd = vi.fn();
    const { result: hook } = renderHook(() => useGame(onEnd));
    await act(async () => {
      await hook.current.start(OPTIONS);
    });
    act(() => {
      hook.current.pick({ kind: "point", longitude: 1, latitude: 1 });
    });
    await act(async () => {
      await hook.current.submit();
    });

    await waitFor(() => {
      expect(onEnd).toHaveBeenCalledOnce();
    });

    act(() => {
      hook.current.advance();
    });
    expect(hook.current.state.phase).toBe("finished");
  });

  it("без поставленной точки не отправляет догадку", async () => {
    start.mockResolvedValue({ session: session(), current_round: round(1), results: [] });

    const { result: hook } = renderHook(() => useGame(vi.fn()));
    await act(async () => {
      await hook.current.start(OPTIONS);
    });
    await act(async () => {
      await hook.current.submit();
    });

    expect(guess).not.toHaveBeenCalled();
    expect(hook.current.state.phase).toBe("playing");
  });

  it("досрочное завершение подводит итоги", async () => {
    start.mockResolvedValue({ session: session(), current_round: round(1), results: [] });
    finish.mockResolvedValue({
      session: session({ status: "abandoned", finished_at: "2026-08-27T10:05:00Z" }),
      current_round: null,
      results: [result(1, 300)],
    });

    const onEnd = vi.fn();
    const { result: hook } = renderHook(() => useGame(onEnd));
    await act(async () => {
      await hook.current.start(OPTIONS);
    });
    await act(async () => {
      await hook.current.quit();
    });

    expect(hook.current.state.phase).toBe("finished");
    expect(hook.current.state.session?.status).toBe("abandoned");
    expect(onEnd).toHaveBeenCalledOnce();
  });

  it("подсказка заменяет раунд ответом сервера и не гасит экран", async () => {
    start.mockResolvedValue({ session: session(), current_round: round(1), results: [] });
    hint.mockResolvedValue(
      round(1, { hint: { label: "Страна", value: "Франция" }, hint_cost: 0, max_score: 3500 }),
    );

    const { result: hook } = renderHook(() => useGame(vi.fn()));
    await act(async () => {
      await hook.current.start(OPTIONS);
    });
    await act(async () => {
      await hook.current.hint();
    });

    expect(hint).toHaveBeenCalledWith(1);
    expect(hook.current.state.phase).toBe("playing");
    expect(hook.current.state.round?.hint?.value).toBe("Франция");
    expect(hook.current.state.round?.max_score).toBe(3500);
  });

  it("вторую подсказку по тому же раунду не запрашивает", async () => {
    start.mockResolvedValue({
      session: session(),
      current_round: round(1, { hint: { label: "Страна", value: "Франция" }, hint_cost: 0 }),
      results: [],
    });

    const { result: hook } = renderHook(() => useGame(vi.fn()));
    await act(async () => {
      await hook.current.start(OPTIONS);
    });
    await act(async () => {
      await hook.current.hint();
    });

    expect(hint).not.toHaveBeenCalled();
  });

  it("продолжает незаконченную партию с текущего раунда", () => {
    const { result: hook } = renderHook(() => useGame(vi.fn()));

    act(() => {
      hook.current.resume({
        session: session({ rounds_done: 1, total_score: 1200 }),
        current_round: round(2),
        results: [result(1, 1200)],
      });
    });

    expect(hook.current.state.phase).toBe("playing");
    expect(hook.current.state.round?.index).toBe(2);
    expect(hook.current.state.results).toHaveLength(1);
  });

  it("сброс возвращает в исходное состояние", async () => {
    start.mockResolvedValue({ session: session(), current_round: round(1), results: [] });

    const { result: hook } = renderHook(() => useGame(vi.fn()));
    await act(async () => {
      await hook.current.start(OPTIONS);
    });
    act(() => {
      hook.current.reset();
    });

    expect(hook.current.state).toMatchObject({ phase: "idle", session: null, round: null });
  });
});
