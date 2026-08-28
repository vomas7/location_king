/**
 * Карточка друзей.
 *
 * Сеть подменена: проверяется, что видит игрок и что уходит на сервер.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Friend, FriendList } from "~/api/types";

const list = vi.fn();
const invite = vi.fn();
const accept = vi.fn();
const remove = vi.fn();

vi.mock("~/api/endpoints", () => ({
  friends: {
    list: (): unknown => list() as unknown,
    invite: (...args: unknown[]): unknown => invite(...args) as unknown,
    accept: (...args: unknown[]): unknown => accept(...args) as unknown,
    remove: (...args: unknown[]): unknown => remove(...args) as unknown,
  },
}));

const { Friends } = await import("~/components/home/Friends");

function friend(overrides: Partial<Friend> = {}): Friend {
  return {
    id: 1,
    display_name: "Приятель",
    avatar: { shape: 0, color: 0 },
    rating: 1000,
    accepted: true,
    incoming: false,
    created_at: "2026-08-28T10:00:00Z",
    ...overrides,
  };
}

function answer(friends: Friend[]): FriendList {
  return { my_code: "AB3K9X", friends };
}

async function show(friends: Friend[] = []) {
  list.mockResolvedValue(answer(friends));
  render(<Friends onError={vi.fn()} />);
  await waitFor(() => {
    expect(screen.getByText("AB3K9X")).toBeTruthy();
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText: vi.fn().mockResolvedValue(undefined) },
  });
});

describe("друзья", () => {
  it("показывает собственный код игрока", async () => {
    await show();

    expect(screen.getByText("Пока никого. Обменяйся кодами — и увидишь общий зачёт.")).toBeTruthy();
  });

  it("зовёт по коду и перечитывает список", async () => {
    await show();
    invite.mockResolvedValue(friend({ accepted: false }));

    fireEvent.change(screen.getByLabelText(/Код друга/), { target: { value: "cd4m8y" } });
    fireEvent.click(screen.getByRole("button", { name: "Позвать" }));

    await waitFor(() => {
      expect(invite).toHaveBeenCalledWith("CD4M8Y");
    });
    expect(list).toHaveBeenCalledTimes(2);
  });

  it("неполный код звать не даёт", async () => {
    await show();

    fireEvent.change(screen.getByLabelText(/Код друга/), { target: { value: "AB3" } });

    expect(screen.getByRole("button", { name: "Позвать" }).hasAttribute("disabled")).toBe(true);
  });

  it("входящую заявку можно принять", async () => {
    await show([friend({ accepted: false, incoming: true })]);
    accept.mockResolvedValue(friend());

    expect(screen.getByText("зовёт тебя")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Принять" }));

    await waitFor(() => {
      expect(accept).toHaveBeenCalledWith(1);
    });
  });

  it("свою неотвеченную заявку видно как ожидание", async () => {
    await show([friend({ accepted: false, incoming: false })]);

    expect(screen.getByText("ждёт ответа")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Принять" })).toBeNull();
  });

  it("связь можно убрать", async () => {
    await show([friend()]);
    remove.mockResolvedValue(undefined);

    fireEvent.click(screen.getByRole("button", { name: "Убрать Приятель" }));

    await waitFor(() => {
      expect(remove).toHaveBeenCalledWith(1);
    });
  });

  it("входящие заявки идут первыми", async () => {
    await show([
      friend({ id: 1, display_name: "Друг", accepted: true }),
      friend({ id: 2, display_name: "Новичок", accepted: false, incoming: true }),
    ]);

    const names = screen.getAllByRole("listitem").map((item) => item.textContent ?? "");

    expect(names[0]).toContain("Новичок");
    expect(names[1]).toContain("Друг");
  });
});
