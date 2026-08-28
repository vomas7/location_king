/**
 * Тесты смены имени.
 *
 * Сеть и контекст авторизации подменены: проверяется, что видит игрок и что
 * уходит на сервер.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { UserProfile } from "~/api/types";

const rename = vi.fn();
const accept = vi.fn();

vi.mock("~/api/endpoints", () => ({
  auth: {
    rename: (...args: unknown[]): unknown => rename(...args) as unknown,
  },
}));

const user: UserProfile = {
  id: 1,
  username: "player",
  display_name: "Игрок A1B2",
  email: "player@example.com",
  total_score: 0,
  games_played: 0,
  total_rounds: 0,
  best_score: 0,
  average_score: null,
  average_distance: null,
  created_at: "2026-01-01T00:00:00Z",
};

vi.mock("~/state/authContext", () => ({
  useAuth: () => ({ user, accept }),
}));

const { DisplayName } = await import("~/components/home/DisplayName");

function startEditing() {
  render(<DisplayName />);
  fireEvent.click(screen.getByRole("button", { name: "Изменить" }));
  return screen.getByLabelText(/Имя в таблице/);
}

describe("смена имени", () => {
  beforeEach(() => {
    rename.mockReset();
    accept.mockReset();
  });

  it("показывает текущее имя", () => {
    render(<DisplayName />);

    expect(screen.getByText("Игрок A1B2")).toBeTruthy();
  });

  it("отправляет новое имя и принимает обновлённый профиль", async () => {
    const renamed = { ...user, display_name: "Гео Король" };
    rename.mockResolvedValue(renamed);

    const input = startEditing();
    fireEvent.change(input, { target: { value: "Гео Король" } });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => {
      expect(rename).toHaveBeenCalledWith("Гео Король");
    });
    expect(accept).toHaveBeenCalledWith(renamed);
  });

  it("не ходит на сервер, если имя не изменилось", async () => {
    const input = startEditing();
    fireEvent.change(input, { target: { value: "  Игрок A1B2  " } });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Изменить" })).toBeTruthy();
    });
    expect(rename).not.toHaveBeenCalled();
  });

  it("показывает причину отказа от сервера", async () => {
    const { ApiError } = await import("~/api/client");
    rename.mockRejectedValue(new ApiError(400, "Имя короче 2 символов"));

    const input = startEditing();
    fireEvent.change(input, { target: { value: "К" } });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    expect(await screen.findByText("Имя короче 2 символов")).toBeTruthy();
    expect(accept).not.toHaveBeenCalled();
  });

  it("отмена возвращает прежнее имя", () => {
    const input = startEditing();
    fireEvent.change(input, { target: { value: "Другое" } });
    fireEvent.click(screen.getByRole("button", { name: "Отмена" }));

    expect(screen.getByText("Игрок A1B2")).toBeTruthy();
  });
});
