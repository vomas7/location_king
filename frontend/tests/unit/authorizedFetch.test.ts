/**
 * Загрузка тайлов с истёкшим токеном.
 *
 * Токен доступа живёт пятнадцать минут, а раунд запросто длится дольше. Если
 * загрузчик снимка не умеет обновлять токен, посреди партии карта начинает
 * отвечать 401 и игрок видит дыры вместо снимка.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { authorizedFetch } from "~/api/client";
import { getTokens, setTokens } from "~/api/tokens";

const OLD = {
  access_token: "старый",
  refresh_token: "обновление",
  token_type: "bearer",
  expires_in: 900,
};
const NEW = {
  access_token: "новый",
  refresh_token: "обновление-2",
  token_type: "bearer",
  expires_in: 900,
};

function tile(status: number): Response {
  return new Response(status === 200 ? "картинка" : "", { status });
}

function authorizationOf(call: unknown[]): string {
  const init = call[1] as RequestInit;
  return (init.headers as Record<string, string>).Authorization ?? "";
}

describe("загрузка с авторизацией", () => {
  beforeEach(() => {
    setTokens(OLD);
    vi.restoreAllMocks();
  });

  it("отдаёт тайл, когда токен ещё жив", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(tile(200));

    const response = await authorizedFetch("/api/rounds/1/tiles/0/0/0.jpg");

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(authorizationOf(fetchMock.mock.calls[0] ?? [])).toBe("Bearer старый");
  });

  it("обновляет токен и повторяет запрос при 401", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(tile(401))
      .mockResolvedValueOnce(new Response(JSON.stringify(NEW), { status: 200 }))
      .mockResolvedValueOnce(tile(200));

    const response = await authorizedFetch("/api/rounds/1/tiles/0/0/0.jpg");

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(3);

    // Повтор уходит уже с новым токеном, иначе смысла в обновлении нет
    expect(authorizationOf(fetchMock.mock.calls[2] ?? [])).toBe("Bearer новый");
    expect(getTokens()?.access_token).toBe("новый");
  });

  it("не зацикливается, когда обновить токен не вышло", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(tile(401))
      .mockResolvedValueOnce(new Response("", { status: 401 }));

    const response = await authorizedFetch("/api/rounds/1/tiles/0/0/0.jpg");

    expect(response.status).toBe(401);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    // Сессия сброшена: с мёртвым токеном обновления играть всё равно нельзя
    expect(getTokens()).toBeNull();
  });
});
