/**
 * Условия партии как зачёт в таблице лидеров.
 *
 * Одно и то же место в двух видах: строкой запроса для сервера и подписью для
 * игрока. Держатся рядом, потому что расходиться им нельзя — иначе экран
 * скажет «Хардкор», а место посчитается по всем партиям сразу.
 */

import type { StartSessionOptions } from "~/api/types";

const LEVELS: Record<string, string> = {
  easy: "Легко",
  normal: "Средне",
  hard: "Сложно",
  hardcore: "Хардкор",
};

const COUNTRIES: Record<string, string> = {
  russia: "Россия",
  usa: "США",
  eu: "Евросоюз",
};

const CONTINENTS: Record<string, string> = {
  europe: "Европа",
  asia: "Азия",
  africa: "Африка",
  north_america: "Сев. Америка",
  south_america: "Юж. Америка",
  oceania: "Океания",
};

/** Строка запроса к таблице лидеров под условия партии. */
export function scopeQuery(options: StartSessionOptions): string {
  const parts = [`difficulty=${options.difficulty}`];

  if (options.country_group !== null) parts.push(`country_group=${options.country_group}`);
  if (options.continent !== null) parts.push(`continent=${options.continent}`);

  return parts.join("&");
}

/** Как назвать этот зачёт игроку. */
export function scopeLabel(options: StartSessionOptions): string {
  const parts = [LEVELS[options.difficulty] ?? options.difficulty];

  if (options.country_group !== null) {
    parts.push(COUNTRIES[options.country_group] ?? options.country_group);
  }
  if (options.continent !== null) {
    parts.push(CONTINENTS[options.continent] ?? options.continent);
  }

  return parts.join(" · ");
}
