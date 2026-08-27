/**
 * Форматирование чисел и дат для интерфейса.
 *
 * Чистые функции без зависимостей от React и сети — их можно звать откуда
 * угодно и проверять по отдельности.
 */

/** Разряды числа разделены неразрывным пробелом. */
export function formatNumber(value: number): string {
  return Math.round(value).toLocaleString("ru-RU");
}

/** Расстояние: метры под километром, километры дальше. */
export function formatDistance(km: number | string | null): string {
  const value = typeof km === "string" ? Number.parseFloat(km) : km;

  if (value === null || !Number.isFinite(value)) return "—";
  if (value < 1) return `${String(Math.round(value * 1000))} м`;
  if (value < 100) return `${value.toFixed(1)} км`;

  return `${formatNumber(value)} км`;
}

/** Размер показанного участка. */
export function formatExtent(km: number | string): string {
  const value = typeof km === "string" ? Number.parseFloat(km) : km;
  return value < 10 ? `${value.toFixed(1)} км` : `${String(Math.round(value))} км`;
}

export function formatPercent(value: string | number | null): string {
  const parsed = typeof value === "string" ? Number.parseFloat(value) : value;
  return parsed === null || !Number.isFinite(parsed) ? "—" : `${String(Math.round(parsed))}%`;
}

/** Дата без времени: «26 августа 2026». */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/** Правильная форма слова после числительного. */
export function plural(count: number, one: string, few: string, many: string): string {
  const mod10 = count % 10;
  const mod100 = count % 100;

  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;

  return many;
}
