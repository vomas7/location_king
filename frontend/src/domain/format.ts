/**
 * Форматирование чисел, расстояний и дат для интерфейса.
 *
 * Чистые функции без зависимостей от React и сети — их можно звать откуда
 * угодно и проверять по отдельности.
 *
 * Всё здесь зависит от языка, и не только словами: русский разделяет разряды
 * пробелом и пишет «1,2 км», английский — запятой и «1.2 km». Поэтому набор
 * собирается на выбранный язык один раз, а компоненты берут готовый через
 * `useFormats()`.
 */

import type { Language } from "~/domain/language";
import { LOCALES } from "~/domain/language";

export interface Formats {
  /** Разряды числа разделены неразрывным пробелом. */
  number(value: number): string;
  /** Расстояние: метры под километром, километры дальше. */
  distance(km: number | string | null): string;
  /** Размер показанного участка. */
  extent(km: number | string): string;
  percent(value: string | number | null): string;
  /** Дата без времени: «26 августа 2026». */
  date(iso: string): string;
  /** День без года: «26 августа». Год у сегодняшнего челленджа лишний */
  day(iso: string): string;
  /** Ограничение времени на раунд. */
  timeLimit(seconds: number | null): string;
}

/** Единицы измерения на каждом языке. Их немного, и словарь им не нужен. */
const UNITS: Record<Language, { m: string; km: string; sec: string; min: string; free: string }> = {
  ru: { m: "м", km: "км", sec: "сек", min: "мин", free: "Без лимита" },
  en: { m: "m", km: "km", sec: "s", min: "min", free: "No limit" },
};

/** Прочерк там, где числа нет: пустое место читается как «ноль». */
const NOTHING = "—";

function build(language: Language): Formats {
  const locale = LOCALES[language];
  const units = UNITS[language];

  const number = (value: number): string => Math.round(value).toLocaleString(locale);

  const decimal = (value: number): string =>
    value.toLocaleString(locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  return {
    number,

    distance(km) {
      const value = typeof km === "string" ? Number.parseFloat(km) : km;

      if (value === null || !Number.isFinite(value)) return NOTHING;
      if (value < 1) return `${String(Math.round(value * 1000))} ${units.m}`;
      if (value < 100) return `${decimal(value)} ${units.km}`;

      return `${number(value)} ${units.km}`;
    },

    extent(km) {
      const value = typeof km === "string" ? Number.parseFloat(km) : km;
      return value < 10 ? `${decimal(value)} ${units.km}` : `${number(value)} ${units.km}`;
    },

    percent(value) {
      const parsed = typeof value === "string" ? Number.parseFloat(value) : value;
      return parsed === null || !Number.isFinite(parsed) ? NOTHING : `${number(parsed)}%`;
    },

    date(iso) {
      return new Date(iso).toLocaleDateString(locale, {
        day: "numeric",
        month: "long",
        year: "numeric",
      });
    },

    day(iso) {
      return new Date(iso).toLocaleDateString(locale, { day: "numeric", month: "long" });
    },

    timeLimit(seconds) {
      if (seconds === null) return units.free;
      return seconds < 60
        ? `${String(seconds)} ${units.sec}`
        : `${String(seconds / 60)} ${units.min}`;
    },
  };
}

const READY: Record<Language, Formats> = { ru: build("ru"), en: build("en") };

/** Набор для выбранного языка. Собран заранее: языков всего два. */
export function formats(language: Language): Formats {
  return READY[language];
}

/**
 * Правильная форма русского слова после числительного.
 *
 * Живёт здесь, а не в словаре: словарь её зовёт, но само правило — про язык,
 * а не про игру.
 */
export function plural(count: number, one: string, few: string, many: string): string {
  const mod10 = count % 10;
  const mod100 = count % 100;

  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;

  return many;
}
