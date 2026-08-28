/**
 * Ссылка-приглашение в комнату.
 *
 * Роутера в приложении нет, поэтому приглашение — это адрес игры с параметром
 * `?room=CODE`: перейдя по нему, игрок сразу видит комнату.
 */

import { CODE_LENGTH, normalizeCode } from "~/domain/codes";

export const ROOM_PARAM = "room";

export function roomLink(code: string, origin: string, path: string): string {
  return `${origin}${path}?${ROOM_PARAM}=${encodeURIComponent(code)}`;
}

/** Код комнаты из строки запроса, если по ссылке пришли в комнату. */
export function roomFromSearch(search: string): string | null {
  const code = normalizeCode(new URLSearchParams(search).get(ROOM_PARAM) ?? "");
  return code.length === CODE_LENGTH ? code : null;
}
