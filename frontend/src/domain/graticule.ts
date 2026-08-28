/**
 * Координатная сетка первого экрана.
 *
 * Сетка не декоративная решётка: её линии — настоящие меридианы и параллели
 * через тридцать градусов, а подпись под прицелом показывает координаты той
 * точки, на которую он наведён. Поэтому по вертикали линии стоят неравномерно
 * — так выглядит проекция Меркатора, та самая, в которой игрок ищет место на
 * карте мира.
 *
 * Чисто и без DOM: проверять такое надо арифметикой, а не скриншотом.
 */

/**
 * Докуда тянется сетка по широте. Полный Меркатор уходит к 85°, где полярная
 * растяжка съедает всю высоту: на 72° видно и растяжку, и приличный кусок
 * обитаемой земли.
 */
export const LAT_LIMIT = 72;

/** Меридианы: каждые тридцать градусов, края не рисуем. */
export const MERIDIANS = [-150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150];

/** Параллели: те же тридцать градусов. Экватор среди них главный. */
export const PARALLELS = [-60, -30, 0, 30, 60];

/** Ордината Меркатора в радианах. Обратная к ней — latitudeAt. */
export function mercatorY(latitude: number): number {
  const radians = (latitude * Math.PI) / 180;
  return Math.log(Math.tan(Math.PI / 4 + radians / 2));
}

const LIMIT_Y = mercatorY(LAT_LIMIT);

/** Долгота точки, отстоящей на долю `ratio` от левого края. */
export function longitudeAt(ratio: number): number {
  return clamp(ratio, 0, 1) * 360 - 180;
}

/** Широта точки, отстоящей на долю `ratio` от верхнего края. */
export function latitudeAt(ratio: number): number {
  const y = LIMIT_Y * (1 - 2 * clamp(ratio, 0, 1));
  return (2 * Math.atan(Math.exp(y)) - Math.PI / 2) * (180 / Math.PI);
}

/** Доля высоты, на которой лежит параллель. Ноль — верх сетки. */
export function parallelOffset(latitude: number): number {
  return (1 - mercatorY(latitude) / LIMIT_Y) / 2;
}

/** Доля ширины, на которой лежит меридиан. */
export function meridianOffset(longitude: number): number {
  return (longitude + 180) / 360;
}

/**
 * Координаты так, как их читают вслух: полушарие буквой, а не знаком минус.
 */
export function formatCoordinates(latitude: number, longitude: number): string {
  const north = latitude >= 0 ? "с. ш." : "ю. ш.";
  const east = longitude >= 0 ? "в. д." : "з. д.";

  return `${degrees(latitude)} ${north} · ${degrees(longitude)} ${east}`;
}

function degrees(value: number): string {
  return `${Math.abs(value).toFixed(2)}°`;
}

function clamp(value: number, low: number, high: number): number {
  return Math.min(Math.max(value, low), high);
}
