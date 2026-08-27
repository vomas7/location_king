/**
 * Тесты транспорта: заголовки, разбор ошибок и обновление токена.
 *
 * Модули клиента и хранилища токенов держат состояние на уровне модуля,
 * поэтому каждый тест импортирует их заново.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { TokenPair } from "~/api/types";

const TOKENS: TokenPair = {
  access_token: "access-1",
  refresh_token: "refresh-1",
  token_type: "bearer",
  expires_in: 900,
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function loadModules() {
  vi.resetModules();
  const tokens = await import("~/api/tokens");
  const client = await import("~/api/client");
  return { tokens, client };
}

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

afterEach(() => {
  localStorage.clear();
});

describe("хранение токенов", () => {
  it("переживает перезагрузку страницы", async () => {
    const first = await loadModules();
    first.tokens.setTokens(TOKENS);

    const second = await loadModules();
    expect(second.tokens.getTokens()).toEqual(TOKENS);
    expect(second.tokens.hasSession()).toBe(true);
  });

  it("забывается при выходе", async () => {
    const { tokens } = await loadModules();
    tokens.setTokens(TOKENS);
    tokens.setTokens(null);

    expect(tokens.hasSession()).toBe(false);
    expect(tokens.authHeaders()).toEqual({});
  });

  it("переживает мусор в хранилище", async () => {
    localStorage.setItem("location-king:session", "{не json");

    const { tokens } = await loadModules();
    expect(tokens.getTokens()).toBeNull();
  });
});

describe("request", () => {
  it("подставляет заголовок авторизации", async () => {
    const { tokens, client } = await loadModules();
    tokens.setTokens(TOKENS);

    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await client.request("/api/auth/me");

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer access-1");
  });

  it("не отправляет тело у GET", async () => {
    const { client } = await loadModules();
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}));
    vi.stubGlobal("fetch", fetchMock);

    await client.request("/api/zones");

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBeUndefined();
  });

  it("превращает detail в ApiError", async () => {
    const { client } = await loadModules();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "Так нельзя" }, 409)));

    await expect(
      client.request("/api/sessions", { method: "POST", body: {} }),
    ).rejects.toMatchObject({ status: 409, detail: "Так нельзя" });
  });

  it("склеивает ошибки валидации", async () => {
    const { client } = await loadModules();
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(jsonResponse({ detail: [{ msg: "поле A" }, { msg: "поле B" }] }, 422)),
    );

    await expect(client.request("/api/sessions")).rejects.toMatchObject({
      detail: "поле A; поле B",
    });
  });

  it("на 401 обновляет токен и повторяет запрос", async () => {
    const { tokens, client } = await loadModules();
    tokens.setTokens(TOKENS);

    const refreshed: TokenPair = { ...TOKENS, access_token: "access-2" };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ detail: "Токен истёк" }, 401))
      .mockResolvedValueOnce(jsonResponse(refreshed))
      .mockResolvedValueOnce(jsonResponse({ id: 7 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(client.request<{ id: number }>("/api/auth/me")).resolves.toEqual({ id: 7 });

    expect(fetchMock.mock.calls[1]?.[0]).toContain("/api/auth/refresh");
    expect(tokens.getTokens()?.access_token).toBe("access-2");
  });

  it("если обновить не удалось — забывает сессию", async () => {
    const { tokens, client } = await loadModules();
    tokens.setTokens(TOKENS);

    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(jsonResponse({ detail: "Токен истёк" }, 401))
        .mockResolvedValueOnce(jsonResponse({ detail: "Недействителен" }, 401)),
    );

    await expect(client.request("/api/auth/me")).rejects.toMatchObject({ status: 401 });
    expect(tokens.hasSession()).toBe(false);
  });

  it("на входе не пытается обновлять токен", async () => {
    const { client } = await loadModules();
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ detail: "Неверный пароль" }, 401));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      client.request("/api/auth/login", { method: "POST", body: {}, skipRefresh: true }),
    ).rejects.toMatchObject({ status: 401 });

    expect(fetchMock).toHaveBeenCalledOnce();
  });
});

describe("tileUrl", () => {
  it("подставляет координаты тайла", async () => {
    const { client } = await loadModules();

    expect(client.tileUrl("/api/rounds/5/tiles/{z}/{x}/{y}.jpg", 2, 3, 1)).toBe(
      "/api/rounds/5/tiles/2/3/1.jpg",
    );
  });
});
