/**
 * Условия партии как зачёт в таблице лидеров.
 *
 * Одно и то же место в двух видах: строкой запроса для сервера и подписью для
 * игрока. Держатся рядом, потому что расходиться им нельзя — иначе экран
 * скажет «Хардкор», а место посчитается по всем партиям сразу.
 *
 * Подписи не свои: и уровни, и места уже названы в словаре, там же, где их
 * выбирают. Второй список тех же слов однажды разошёлся бы с первым.
 */

import type { StartSessionOptions } from "~/api/types";
import type { PlaceKey } from "~/domain/place";
import { PLACES } from "~/domain/setup";
import type { Dictionary } from "~/i18n/dictionary";

/** Строка запроса к таблице лидеров под условия партии. */
export function scopeQuery(options: StartSessionOptions): string {
  const parts = [`difficulty=${options.difficulty}`];

  if (options.country_group !== null) parts.push(`country_group=${options.country_group}`);
  if (options.continent !== null) parts.push(`continent=${options.continent}`);

  return parts.join("&");
}

/**
 * Как назвать место игроку. Неизвестный код показываем как есть: он пришёл
 * из условий партии, и промолчать о нём было бы хуже.
 */
function placeLabel(key: PlaceKey, code: string, text: Dictionary): string {
  const found = PLACES.find((place) => place.value === key);
  return found === undefined ? code : text.setup.places[found.name];
}

/** Как назвать этот зачёт игроку. */
export function scopeLabel(options: StartSessionOptions, text: Dictionary): string {
  const levels: Record<string, { label: string }> = text.setup.levels;
  const parts = [levels[options.difficulty]?.label ?? options.difficulty];

  if (options.country_group !== null) {
    parts.push(placeLabel(`country:${options.country_group}`, options.country_group, text));
  }
  if (options.continent !== null) {
    parts.push(placeLabel(`continent:${options.continent}`, options.continent, text));
  }

  return parts.join(" · ");
}
