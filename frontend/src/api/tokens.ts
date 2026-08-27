/**
 * Хранение пары токенов.
 *
 * Вынесено из клиента API, потому что заголовок авторизации нужен ещё и
 * загрузчику тайлов: обычный <img src> заголовки не отправляет.
 */

import type { TokenPair } from "~/api/types";

/** Ключ в localStorage. Он назван в документе про хранилище, и тест это сверяет. */
export const SESSION_STORAGE_KEY = "location-king:session";

let tokens: TokenPair | null = read();

function read(): TokenPair | null {
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY);
    return raw === null ? null : (JSON.parse(raw) as TokenPair);
  } catch {
    // Приватный режим или испорченное значение: играем без запоминания сессии
    return null;
  }
}

export function getTokens(): TokenPair | null {
  return tokens;
}

export function setTokens(value: TokenPair | null): void {
  tokens = value;

  try {
    if (value === null) {
      localStorage.removeItem(SESSION_STORAGE_KEY);
    } else {
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(value));
    }
  } catch {
    // Записать не вышло — токены останутся только в памяти вкладки
  }
}

export function hasSession(): boolean {
  return tokens !== null;
}

/** Заголовок авторизации или пустой объект, если токена нет. */
export function authHeaders(): Record<string, string> {
  return tokens === null ? {} : { Authorization: `Bearer ${tokens.access_token}` };
}
