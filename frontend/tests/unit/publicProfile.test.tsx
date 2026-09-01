/**
 * Публичное лицо игрока: имя и аватарка.
 *
 * Сеть и контекст авторизации подменены: проверяется, что видит игрок и что
 * уходит на сервер.
 */

import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithLanguage as render } from "./withLanguage";

import type { UserProfile } from "~/api/types";

const updateProfile = vi.fn();
const accept = vi.fn();

vi.mock("~/api/endpoints", () => ({
  auth: {
    updateProfile: (...args: unknown[]): unknown => updateProfile(...args) as unknown,
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
  rating: 1000,
  duels_played: 0,
  theme: "dark",
  avatar: { shape: 0, color: 0, image_url: null },
  created_at: "2026-01-01T00:00:00Z",
};

vi.mock("~/state/authContext", () => ({
  useAuth: () => ({ user, accept }),
}));

const { PublicProfile } = await import("~/components/home/PublicProfile");

function startEditing() {
  render(<PublicProfile />);
  fireEvent.click(screen.getByRole("button", { name: "Изменить" }));
  return screen.getByLabelText(/Имя в таблице/);
}

describe("публичное лицо игрока", () => {
  beforeEach(() => {
    updateProfile.mockReset();
    accept.mockReset();
  });

  it("показывает текущее имя", () => {
    render(<PublicProfile />);

    expect(screen.getByText("Игрок A1B2")).toBeTruthy();
  });

  it("отправляет новое имя и принимает обновлённый профиль", async () => {
    const renamed = { ...user, display_name: "Гео Король" };
    updateProfile.mockResolvedValue(renamed);

    const input = startEditing();
    fireEvent.change(input, { target: { value: "Гео Король" } });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => {
      expect(updateProfile).toHaveBeenCalledWith({ display_name: "Гео Король" });
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
    expect(updateProfile).not.toHaveBeenCalled();
  });

  it("показывает причину отказа от сервера", async () => {
    const { ApiError } = await import("~/api/client");
    updateProfile.mockRejectedValue(new ApiError(400, "Имя короче 2 символов"));

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

describe("аватарка", () => {
  beforeEach(() => {
    updateProfile.mockReset();
    accept.mockReset();
  });

  it("узор меняется и уходит на сервер вместе с цветом", async () => {
    updateProfile.mockResolvedValue({ ...user, avatar: { shape: 2, color: 0, image_url: null } });

    startEditing();
    fireEvent.click(screen.getByRole("radio", { name: "Узор 3" }));
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => {
      expect(updateProfile).toHaveBeenCalledWith({ avatar_shape: 2, avatar_color: 0 });
    });
  });

  it("имя и аватарка уходят одним запросом", async () => {
    updateProfile.mockResolvedValue(user);

    const input = startEditing();
    fireEvent.change(input, { target: { value: "Штурман" } });
    fireEvent.click(screen.getByRole("radio", { name: "Цвет 4" }));
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => {
      expect(updateProfile).toHaveBeenCalledWith({
        display_name: "Штурман",
        avatar_shape: 0,
        avatar_color: 3,
      });
    });
  });

  it("без изменений сервер не беспокоим", async () => {
    startEditing();
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Изменить" })).toBeTruthy();
    });
    expect(updateProfile).not.toHaveBeenCalled();
  });
});
