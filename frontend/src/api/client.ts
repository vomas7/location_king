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

/**
 * Что показать игроку, когда запрос не удался.
 *
 * У ApiError есть человеческое объяснение от сервера — его и показываем.
 * Всё остальное (обрыв связи, отказ разбора) объяснить нечем, поэтому туда
 * подставляется запасной текст, свой у каждого места.
 */
export function errorMessage(error: unknown, fallback = "Сервер недоступен. Попробуй ещё раз") {
  return error instanceof ApiError ? error.detail : fallback;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  /** Объект уедет как JSON, FormData — как есть: так отправляется файл. */
  body?: unknown;
  /** Не пытаться обновить токен при 401 — для самих запросов авторизации. */
  skipRefresh?: boolean;
}

interface ValidationDetail {
  msg?: string;
}

async function readError(response: Response): Promise<string> {
  // Отказ по частоте может прийти не только от приложения, но и от nginx —
  // тот отвечает своей страницей, и разбирать в ней нечего. Игроку в обоих
  // случаях нужно одно и то же: подождать
  if (response.status === 429) {
    return "Слишком часто. Подожди немного и попробуй снова";
  }

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

/**
 * Запрос с авторизацией, минуя разбор JSON.
 *
 * Нужен загрузчику тайлов: он забирает картинку, а не объект. Обновление
 * токена при этом обязано быть общим — токен доступа живёт пятнадцать минут,
 * и раунд запросто длится дольше. Без обновления снимок посреди партии
 * начинал бы отвечать 401, и игрок видел бы дыры вместо карты.
 */
export async function authorizedFetch(url: string): Promise<Response> {
  const response = await fetch(url, { headers: authHeaders() });

  if (response.status !== 401 || !(await refreshTokens())) {
    return response;
  }

  return fetch(url, { headers: authHeaders() });
}

/** Запрос к API. При 401 один раз пробует обновить токен и повторить. */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, skipRefresh = false } = options;

  const hasBody = body !== undefined;

  // У FormData свой Content-Type с границей блоков, и проставляет его
  // браузер. Свой заголовок здесь сломал бы разбор на сервере
  const isForm = body instanceof FormData;

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      ...authHeaders(),
      ...(hasBody && !isForm ? { "Content-Type": "application/json" } : {}),
    },
    ...(hasBody ? { body: isForm ? body : JSON.stringify(body) } : {}),
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

/**
 * Запрос, ответ которого нужен строкой.
 *
 * Контуры стран весят полмегабайта и уходят прямо в разборщик OpenLayers.
 * Прогонять их через JSON.parse и обратно в строку — двойная работа над
 * тем, что и так приедет разобранным.
 */
export async function requestText(path: string): Promise<string> {
  const response = await authorizedFetch(`${API_BASE}${path}`);

  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }

  return response.text();
}

/** Абсолютный адрес тайла раунда по локальным координатам. */
export function tileUrl(template: string, z: number, x: number, y: number): string {
  return `${API_BASE}${template}`
    .replace("{z}", String(z))
    .replace("{x}", String(x))
    .replace("{y}", String(y));
}
