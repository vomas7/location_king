/**
 * Поиск соперника.
 *
 * Сеть подменена целиком: проверяется, что делает экран, а не API. Время
 * тоже подменено — иначе тест ждал бы опроса по-настоящему.
 */

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { DuelSearch } from "~/api/types";

const searchingCount = vi.fn();
const start = vi.fn();
const poll = vi.fn();
const stop = vi.fn();
const join = vi.fn();
const playBot = vi.fn();

vi.mock("~/api/endpoints", () => ({
  duels: {
    searching: (): unknown => searchingCount() as unknown,
    start: (): unknown => start() as unknown,
    poll: (): unknown => poll() as unknown,
    stop: (): unknown => stop() as unknown,
    playBot: (): unknown => playBot() as unknown,
  },
  matches: {
    join: (...args: unknown[]): unknown => join(...args) as unknown,
  },
}));

const { useDuelSearch } = await import("~/state/useDuelSearch");

function state(searching: number, code: string | null = null, bots = 0): DuelSearch {
  return { searching, code, bots };
}

const SESSION = { session: { id: "s-1" }, current_round: null, results: [] } as unknown;

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers();

  searchingCount.mockResolvedValue(state(0));
  start.mockResolvedValue(state(1));
  poll.mockResolvedValue(state(1));
  stop.mockResolvedValue(undefined);
  join.mockResolvedValue(SESSION);
  playBot.mockResolvedValue(state(0, "BOT7QW"));
});

afterEach(() => {
  vi.useRealTimers();
});

/** Дать отработать промисам, которые уже поставлены в очередь. */
async function settle() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
}

describe("useDuelSearch", () => {
  it("показывает счётчик ещё до того, как игрок встал в очередь", async () => {
    searchingCount.mockResolvedValue(state(4));

    const { result } = renderHook(() => useDuelSearch(vi.fn()));
    await settle();

    expect(result.current.phase).toBe("idle");
    expect(result.current.searching).toBe(4);
  });

  it("начинает поиск и переходит к опросу", async () => {
    const { result } = renderHook(() => useDuelSearch(vi.fn()));
    await settle();

    act(() => {
      result.current.start();
    });
    await settle();

    expect(start).toHaveBeenCalledOnce();
    expect(result.current.phase).toBe("searching");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(poll).toHaveBeenCalled();
  });

  it("найденная пара приводит к входу в дуэль", async () => {
    const onFound = vi.fn();
    poll.mockResolvedValue(state(2, "AB3K9X"));

    const { result } = renderHook(() => useDuelSearch(onFound));
    await settle();

    act(() => {
      result.current.start();
    });
    await settle();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    // Ответ опроса → найденный код → вход в дуэль: три шага через состояние
    await settle();
    await settle();

    expect(join).toHaveBeenCalledWith("AB3K9X");
    expect(onFound).toHaveBeenCalledWith(SESSION);
    expect(result.current.phase).toBe("idle");
  });

  it("отмена возвращает в исходное состояние и снимает с очереди", async () => {
    const { result } = renderHook(() => useDuelSearch(vi.fn()));
    await settle();

    act(() => {
      result.current.start();
    });
    await settle();

    act(() => {
      result.current.stop();
    });
    await settle();

    expect(stop).toHaveBeenCalledOnce();
    expect(result.current.phase).toBe("idle");
  });

  it("отказ сервера прекращает поиск и объясняет причину", async () => {
    start.mockRejectedValue(new Error("нет связи"));

    const { result } = renderHook(() => useDuelSearch(vi.fn()));
    await settle();

    act(() => {
      result.current.start();
    });
    await settle();

    expect(result.current.phase).toBe("idle");
    expect(result.current.error).not.toBeNull();
  });

  it("уход со страницы во время поиска снимает с очереди", async () => {
    const { result, unmount } = renderHook(() => useDuelSearch(vi.fn()));
    await settle();

    act(() => {
      result.current.start();
    });
    await settle();

    unmount();

    expect(stop).toHaveBeenCalledOnce();
  });

  it("боты приезжают тем же счётчиком, что и очередь", async () => {
    searchingCount.mockResolvedValue(state(0, null, 5));

    const { result } = renderHook(() => useDuelSearch(vi.fn()));
    await settle();

    expect(result.current.bots).toBe(5);
  });

  it("дуэль с ботом собирается сразу и приводит в неё", async () => {
    const onFound = vi.fn();

    const { result } = renderHook(() => useDuelSearch(onFound));
    await settle();

    act(() => {
      result.current.playBot();
    });
    // Ответ сервера → найденный код → вход в дуэль
    await settle();
    await settle();

    expect(playBot).toHaveBeenCalledOnce();
    expect(join).toHaveBeenCalledWith("BOT7QW");
    expect(onFound).toHaveBeenCalledWith(SESSION);
    expect(result.current.phase).toBe("idle");
  });

  it("из очереди можно уйти к боту, не отменяя поиск вручную", async () => {
    const { result } = renderHook(() => useDuelSearch(vi.fn()));
    await settle();

    act(() => {
      result.current.start();
    });
    await settle();
    expect(result.current.phase).toBe("searching");

    act(() => {
      result.current.playBot();
    });
    await settle();
    await settle();

    // Очередь покидается на сервере: вторая пара посреди партии не нужна
    expect(join).toHaveBeenCalledWith("BOT7QW");
    expect(result.current.phase).toBe("idle");
  });

  it("отказ в дуэли с ботом объясняется, а экран остаётся рабочим", async () => {
    playBot.mockRejectedValue(new Error("ботов нет"));

    const { result } = renderHook(() => useDuelSearch(vi.fn()));
    await settle();

    act(() => {
      result.current.playBot();
    });
    await settle();

    expect(result.current.error).not.toBeNull();
    expect(result.current.phase).toBe("idle");
    expect(join).not.toHaveBeenCalled();
  });

  it("уход без поиска сервер не беспокоит", async () => {
    const { unmount } = renderHook(() => useDuelSearch(vi.fn()));
    await settle();

    unmount();

    expect(stop).not.toHaveBeenCalled();
  });
});
