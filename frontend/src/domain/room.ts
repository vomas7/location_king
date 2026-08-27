/**
 * Код комнаты и ссылка на неё.
 *
 * Роутера в приложении нет, поэтому приглашение — это адрес игры с параметром
 * `?room=CODE`: перейдя по нему, игрок сразу видит комнату.
 */

export const ROOM_PARAM = "room";

/** Символы кода: без похожих друг на друга, как и на сервере. */
const CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
export const CODE_LENGTH = 6;

/** Привести введённое к виду кода: заглавные, без мусора и лишней длины. */
export function normalizeCode(value: string): string {
  return [...value.toUpperCase()]
    .filter((symbol) => CODE_ALPHABET.includes(symbol))
    .slice(0, CODE_LENGTH)
    .join("");
}

export function isCompleteCode(value: string): boolean {
  return normalizeCode(value).length === CODE_LENGTH;
}

/** Ссылка-приглашение в комнату. */
export function roomLink(code: string, origin: string, path: string): string {
  return `${origin}${path}?${ROOM_PARAM}=${encodeURIComponent(code)}`;
}

/** Код комнаты из строки запроса, если по ссылке пришли в комнату. */
export function roomFromSearch(search: string): string | null {
  const code = normalizeCode(new URLSearchParams(search).get(ROOM_PARAM) ?? "");
  return code.length === CODE_LENGTH ? code : null;
}
