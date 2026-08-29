/**
 * Картинки, которые нельзя просто поставить в src.
 *
 * Аватарки лежат за той же авторизацией, что и всё остальное API, а тег img
 * не умеет отправлять токен: браузер запросит адрес сам, получит 401 и
 * покажет сломанную картинку. Поэтому картинка забирается тем же
 * авторизованным запросом, что и тайлы снимка, и превращается в локальную
 * ссылку на blob.
 *
 * Результат помнится по адресу: одна и та же аватарка стоит в каждой строке
 * таблицы лидеров, и качать её двадцать раз незачем. Адрес несёт версию и
 * меняется, когда игрок меняет картинку, — значит, устареть запомненное не
 * может.
 */

import { API_BASE, authorizedFetch } from "~/api/client";

const loaded = new Map<string, Promise<string | null>>();

async function fetchImage(path: string): Promise<string | null> {
  try {
    const response = await authorizedFetch(`${API_BASE}${path}`);
    if (!response.ok) return null;

    return URL.createObjectURL(await response.blob());
  } catch {
    // Сеть моглa моргнуть. Показывать вместо картинки нечего, и место
    // аватарки займёт узор — он есть у каждого
    return null;
  }
}

/** Локальная ссылка на картинку по её адресу в API. */
export function image(path: string): Promise<string | null> {
  const known = loaded.get(path);
  if (known !== undefined) return known;

  const pending = fetchImage(path);
  loaded.set(path, pending);

  return pending;
}

/** Забыть загруженное — нужно тестам, чтобы соседние не делили кэш. */
export function forgetImages(): void {
  loaded.clear();
}
