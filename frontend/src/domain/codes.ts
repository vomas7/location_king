/**
 * Короткие коды, которые человек набирает руками.
 *
 * Их в игре два вида — код комнаты и код игрока, — и устроены они одинаково:
 * тот же алфавит, что на сервере, без символов, которые путаются на слух.
 */

/** Символы кода: без похожих друг на друга, как и в utils/codes.py. */
const ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

export const CODE_LENGTH = 6;

/** Привести введённое к виду кода: заглавные, без мусора и лишней длины. */
export function normalizeCode(value: string): string {
  return [...value.toUpperCase()]
    .filter((symbol) => ALPHABET.includes(symbol))
    .slice(0, CODE_LENGTH)
    .join("");
}

export function isCompleteCode(value: string): boolean {
  return normalizeCode(value).length === CODE_LENGTH;
}
