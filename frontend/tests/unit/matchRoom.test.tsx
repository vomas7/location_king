/**
 * Тесты карточки комнаты.
 *
 * Сеть подменена целиком: проверяется, что видит игрок и что уходит на сервер,
 * а не сам API.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "~/api/client";
import type { MatchView, SessionState } from "~/api/types";

const create = vi.fn();
const get = vi.fn();
const join = vi.fn();
const close = vi.fn();
const mine = vi.fn();
const session = vi.fn();

vi.mock("~/api/endpoints", () => ({
  matches: {
    create: (...args: unknown[]): unknown => create(...args) as unknown,
    get: (...args: unknown[]): unknown => get(...args) as unknown,
    join: (...args: unknown[]): unknown => join(...args) as unknown,
    close: (...args: unknown[]): unknown => close(...args) as unknown,
    mine: (): unknown => mine() as unknown,
  },
  game: {
    session: (...args: unknown[]): unknown => session(...args) as unknown,
  },
}));

const { MatchRoom } = await import("~/components/home/MatchRoom");

const OPTIONS = {
  rounds_total: 5,
  view_extent_km: 5,
  continent: null,
  country_group: null,
  difficulty: "normal",
  answer_mode: "point",
  time_limit_seconds: null,
};

function room(overrides: Partial<MatchView> = {}): MatchView {
  return {
    code: "AB3K9X",
    status: "open",
    host_name: "Хост",
    is_host: true,
    rounds_total: 5,
    time_limit_seconds: 60,
    players: 0,
    created_at: "2026-08-27T10:00:00Z",
    my_session: null,
    standings: [],
    ...overrides,
  };
}

/** Отрисовать карточку и дождаться, пока подтянется список своих комнат. */
async function renderRoom(onJoined = vi.fn(), onError = vi.fn(), mayStart = vi.fn(() => true)) {
  render(
    <MatchRoom
      options={OPTIONS}
      summary="5 раундов · Средне · 15 км · Весь мир · без таймера"
      refreshKey={0}
      mayStart={mayStart}
      onEditSetup={vi.fn()}
      onJoined={onJoined}
      onError={onError}
    />,
  );

  await waitFor(() => {
    expect(mine).toHaveBeenCalled();
  });

  return { onJoined, onError, mayStart };
}

/** Партия, которую эндпоинт возвращает после входа в комнату. */
function sessionState(id: string): SessionState {
  return {
    session: {
      id,
      status: "active",
      challenge_day: null,
      rounds_total: 5,
      rounds_done: 0,
      total_score: 0,
      average_score: null,
      time_limit_seconds: 60,
      started_at: "2026-08-27T10:00:00Z",
      finished_at: null,
    },
    current_round: null,
    results: [],
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mine.mockResolvedValue({ matches: [] });
  window.history.replaceState(null, "", "/");
});

describe("MatchRoom", () => {
  it("без комнаты предлагает создать или войти по коду", async () => {
    await renderRoom();

    expect(screen.getByRole("button", { name: "Создать комнату" })).toBeTruthy();
    expect(screen.getByLabelText("Код комнаты")).toBeTruthy();
  });

  it("не пускает по недобранному коду", async () => {
    await renderRoom();

    const input = screen.getByLabelText("Код комнаты");
    fireEvent.change(input, { target: { value: "ab3k" } });

    expect(screen.getByRole("button", { name: "Войти" }).hasAttribute("disabled")).toBe(true);

    fireEvent.change(input, { target: { value: "ab3k9x" } });
    expect(screen.getByRole("button", { name: "Войти" }).hasAttribute("disabled")).toBe(false);
  });

  it("созданная комната показывает код и условия", async () => {
    create.mockResolvedValue(room());
    await renderRoom();

    fireEvent.click(screen.getByRole("button", { name: "Создать комнату" }));

    await waitFor(() => {
      expect(screen.getByText("AB3K9X")).toBeTruthy();
    });
    expect(create).toHaveBeenCalledWith(OPTIONS);
    expect(screen.getByText(/1 мин/)).toBeTruthy();
  });

  it("ссылка-приглашение открывает комнату и исчезает из адреса", async () => {
    window.history.replaceState(null, "", "/?room=ab3k9x");
    get.mockResolvedValue(room({ is_host: false, host_name: "Другой" }));

    await renderRoom();

    await waitFor(() => {
      expect(screen.getByText("AB3K9X")).toBeTruthy();
    });
    expect(get).toHaveBeenCalledWith("AB3K9X");
    expect(window.location.search).toBe("");
  });

  it("показывает таблицу: счёт доигравшим, прогресс остальным", async () => {
    create.mockResolvedValue(
      room({
        players: 2,
        standings: [
          {
            rank: 1,
            display_name: "Другой",
            avatar: { shape: 0, color: 0, image_url: null },
            total_score: 4200,
            rounds_done: 5,
            is_finished: true,
            is_you: false,
            finished_at: "2026-08-27T10:20:00Z",
          },
          {
            rank: 2,
            display_name: "Хост",
            avatar: { shape: 0, color: 0, image_url: null },
            total_score: 0,
            rounds_done: 2,
            is_finished: false,
            is_you: true,
            finished_at: null,
          },
        ],
      }),
    );
    await renderRoom();

    fireEvent.click(screen.getByRole("button", { name: "Создать комнату" }));

    await waitFor(() => {
      expect(screen.getByText("Другой")).toBeTruthy();
    });
    expect(screen.getByText("2/5")).toBeTruthy();
  });

  it("вход в комнату отдаёт партию наверх", async () => {
    create.mockResolvedValue(room());
    const started = sessionState("s-1");
    join.mockResolvedValue(started);

    const { onJoined } = await renderRoom();
    fireEvent.click(screen.getByRole("button", { name: "Создать комнату" }));
    fireEvent.click(await screen.findByRole("button", { name: "Играть" }));

    await waitFor(() => {
      expect(onJoined).toHaveBeenCalledWith(started);
    });
    expect(join).toHaveBeenCalledWith("AB3K9X");
  });

  it("начатую партию продолжает, а не входит второй раз", async () => {
    create.mockResolvedValue(
      room({
        my_session: {
          id: "s-1",
          status: "active",
          challenge_day: null,
          rounds_total: 5,
          rounds_done: 2,
          total_score: 1200,
          started_at: "2026-08-27T10:00:00Z",
          finished_at: null,
        },
      }),
    );
    const resumed = sessionState("s-1");
    session.mockResolvedValue(resumed);

    const { onJoined } = await renderRoom();
    fireEvent.click(screen.getByRole("button", { name: "Создать комнату" }));
    fireEvent.click(await screen.findByRole("button", { name: "Продолжить партию" }));

    await waitFor(() => {
      expect(onJoined).toHaveBeenCalledWith(resumed);
    });
    expect(join).not.toHaveBeenCalled();
    expect(session).toHaveBeenCalledWith("s-1");
  });

  it("не входит в комнату, пока незаконченная партия не отпущена", async () => {
    create.mockResolvedValue(room());

    const { onJoined } = await renderRoom(
      vi.fn(),
      vi.fn(),
      vi.fn(() => false),
    );
    fireEvent.click(screen.getByRole("button", { name: "Создать комнату" }));
    fireEvent.click(await screen.findByRole("button", { name: "Играть" }));

    expect(join).not.toHaveBeenCalled();
    expect(onJoined).not.toHaveBeenCalled();
  });

  it("свою партию в комнате продолжает, ни о чём не спрашивая", async () => {
    create.mockResolvedValue(
      room({
        my_session: {
          id: "s-1",
          status: "active",
          challenge_day: null,
          rounds_total: 5,
          rounds_done: 2,
          total_score: 1200,
          started_at: "2026-08-27T10:00:00Z",
          finished_at: null,
        },
      }),
    );
    session.mockResolvedValue(sessionState("s-1"));

    const { mayStart } = await renderRoom(
      vi.fn(),
      vi.fn(),
      vi.fn(() => false),
    );
    fireEvent.click(screen.getByRole("button", { name: "Создать комнату" }));
    fireEvent.click(await screen.findByRole("button", { name: "Продолжить партию" }));

    await waitFor(() => {
      expect(session).toHaveBeenCalledWith("s-1");
    });
    expect(mayStart).not.toHaveBeenCalled();
  });

  it("хост закрывает набор", async () => {
    create.mockResolvedValue(room());
    close.mockResolvedValue(room({ status: "closed" }));

    await renderRoom();
    fireEvent.click(screen.getByRole("button", { name: "Создать комнату" }));
    fireEvent.click(await screen.findByRole("button", { name: "Закрыть набор" }));

    await waitFor(() => {
      expect(screen.getByText(/набор закрыт/)).toBeTruthy();
    });
    expect(close).toHaveBeenCalledWith("AB3K9X");
  });

  it("не хосту кнопки закрытия не показывает", async () => {
    get.mockResolvedValue(room({ is_host: false }));
    window.history.replaceState(null, "", "/?room=AB3K9X");

    await renderRoom();

    await waitFor(() => {
      expect(screen.getByText("AB3K9X")).toBeTruthy();
    });
    expect(screen.queryByRole("button", { name: "Закрыть набор" })).toBeNull();
  });

  it("показывает объяснение сервера, а не своё", async () => {
    // Из api/ приходит ApiError с человеческим объяснением. Обычная ошибка
    // объяснением не является: её текст игроку показывать нельзя
    get.mockRejectedValue(new ApiError(404, "Комната ZZZZZZ не найдена"));

    const { onError } = await renderRoom();
    fireEvent.change(screen.getByLabelText("Код комнаты"), { target: { value: "zzzzzz" } });
    fireEvent.click(screen.getByRole("button", { name: "Войти" }));

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith("Комната ZZZZZZ не найдена");
    });
  });
});
