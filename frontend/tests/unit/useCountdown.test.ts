import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useCountdown } from "~/state/useCountdown";

beforeEach(() => {
  // Хук считает разницу через Date.now, поэтому подменять нужно и часы
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval", "Date"] });
});

afterEach(() => {
  vi.useRealTimers();
});

function inSeconds(seconds: number): string {
  return new Date(Date.now() + seconds * 1000).toISOString();
}

describe("useCountdown", () => {
  it("без срока время не ограничено", () => {
    const { result } = renderHook(() => useCountdown(null));

    expect(result.current.secondsLeft).toBeNull();
    expect(result.current.expired).toBe(false);
  });

  it("считает оставшиеся секунды", () => {
    const deadline = inSeconds(30);
    const { result } = renderHook(() => useCountdown(deadline));

    expect(result.current.secondsLeft).toBe(30);
    expect(result.current.expired).toBe(false);
  });

  it("уменьшает счётчик со временем", () => {
    // Срок считается один раз: если пересчитывать его на каждый рендер, он
    // будет убегать вперёд вместе с часами
    const deadline = inSeconds(10);
    const { result } = renderHook(() => useCountdown(deadline));

    act(() => {
      vi.advanceTimersByTime(4000);
    });

    expect(result.current.secondsLeft).toBe(6);
  });

  it("сообщает, что время вышло", () => {
    const deadline = inSeconds(2);
    const { result } = renderHook(() => useCountdown(deadline));

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(result.current.secondsLeft).toBe(0);
    expect(result.current.expired).toBe(true);
  });

  it("не уходит в минус", () => {
    const deadline = inSeconds(-60);
    const { result } = renderHook(() => useCountdown(deadline));

    expect(result.current.secondsLeft).toBe(0);
    expect(result.current.expired).toBe(true);
  });

  it("перезапускается на новом сроке", () => {
    const { result, rerender } = renderHook(({ deadline }) => useCountdown(deadline), {
      initialProps: { deadline: inSeconds(5) },
    });

    act(() => {
      vi.advanceTimersByTime(4000);
    });
    expect(result.current.secondsLeft).toBe(1);

    rerender({ deadline: inSeconds(60) });
    expect(result.current.secondsLeft).toBe(60);
  });
});
