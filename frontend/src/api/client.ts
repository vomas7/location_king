/**
 * Транспорт запросов к API.
 *
 * Единственное место, которое знает про fetch, коды ответов и обновление
 * токенов. Выше по стеку ходят только доменные типы и ApiError.
 */

import { authHeaders, getTokens, setTokens } from "~/api/tokens";
import type { TokenPair } from "~/api/types";

const runtime = window.__CONFIG__ ?? {};

/** База API. Пустая строка означает тот же origin, что и у страницы. */
export const API_BASE = (runtime.apiBase ?? "").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

interface RequestOptions {
  method?: "GET" | "POST";
  body?: unknown;
  /** Не пытаться обновить токен при 401 — для самих запросов авторизации. */
  skipRefresh?: boolean;
}

interface ValidationDetail {
  msg?: string;
}

async function readError(response: Response): Promise<string> {
  const fallback = `Ошибка ${String(response.status)}`;

  try {
    const body = (await response.json()) as { detail?: string | ValidationDetail[] };

    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((item) => item.msg ?? "").join("; ") || fallback;
    }
    return fallback;
  } catch {
    return fallback;
  }
}

/**
 * Обновление токена, идущее прямо сейчас.
 *
 * При открытии страницы запросы уходят пачкой, и с истёкшим токеном каждый
 * получил бы 401. Без этой ссылки они полезли бы обновляться наперегонки и
 * записали бы друг поверх друга разные пары токенов.
 */
let refreshing: Promise<boolean> | null = null;

async function requestNewTokens(): Promise<boolean> {
  const current = getTokens();
  if (current === null) return false;

  const response = await fetch(`${API_BASE}/api/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: current.refresh_token }),
  });

  if (!response.ok) {
    setTokens(null);
    return false;
  }

  setTokens((await response.json()) as TokenPair);
  return true;
}

function refreshTokens(): Promise<boolean> {
  refreshing ??= requestNewTokens().finally(() => {
    refreshing = null;
  });

  return refreshing;
}

/** Запрос к API. При 401 один раз пробует обновить токен и повторить. */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, skipRefresh = false } = options;

  const hasBody = body !== undefined;

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      ...authHeaders(),
      ...(hasBody ? { "Content-Type": "application/json" } : {}),
    },
    ...(hasBody ? { body: JSON.stringify(body) } : {}),
  });

  if (response.status === 401 && !skipRefresh && (await refreshTokens())) {
    return request<T>(path, { ...options, skipRefresh: true });
  }

  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }

  // 204 приходит без тела, и разбор JSON на нём падает
  if (response.status === 204) return undefined as T;

  return (await response.json()) as T;
}

/** Абсолютный адрес тайла раунда по локальным координатам. */
export function tileUrl(template: string, z: number, x: number, y: number): string {
  return `${API_BASE}${template}`
    .replace("{z}", String(z))
    .replace("{x}", String(x))
    .replace("{y}", String(y));
}
