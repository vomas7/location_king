/**
 * Язык интерфейса.
 *
 * Русский — основной: игра сделана на нём, на нём же написаны названия мест и
 * правовые документы. Английский нужен, чтобы игру можно было показать за
 * пределами русскоязычного интернета, и включается сам, если браузер о
 * русском не просит.
 *
 * Выбор лежит только в браузере, а не в профиле игрока, как тема. Язык — это
 * свойство того, кто сейчас смотрит на экран: одним и тем же аккаунтом можно
 * играть с рабочего ноутбука и с чужого телефона, и переносить туда язык
 * незачем. К тому же выбрать его нужно до всякого входа — посадочная страница
 * читается раньше, чем появляется учётная запись.
 */

export type Language = "ru" | "en";

/** Ключ в localStorage. Он назван в документе про хранилище, и тест это сверяет. */
export const LANGUAGE_STORAGE_KEY = "location-king:language";

/** Как язык называется на самом себе: список выбора не переводят. */
export const LANGUAGES: { value: Language; label: string }[] = [
  { value: "ru", label: "Русский" },
  { value: "en", label: "English" },
];

/** Локаль для чисел и дат. */
export const LOCALES: Record<Language, string> = {
  ru: "ru-RU",
  en: "en-US",
};

export function isLanguage(value: unknown): value is Language {
  return value === "ru" || value === "en";
}

/**
 * Язык, с которого начинается посещение.
 *
 * Прошлый выбор сильнее всего: игрок его сделал руками. Дальше — язык
 * браузера: человеку с английской системой русская страница не говорит
 * ничего, а переключатель он найдёт только в подвале.
 */
export function initialLanguage(): Language {
  const stored = storedLanguage();
  if (stored !== null) return stored;

  return navigator.language.toLowerCase().startsWith("ru") ? "ru" : "en";
}

/** Что лежит в браузере от прошлого раза. Ничего — значит, выбора не было. */
export function storedLanguage(): Language | null {
  try {
    const raw = localStorage.getItem(LANGUAGE_STORAGE_KEY);
    return isLanguage(raw) ? raw : null;
  } catch {
    // Приватный режим: язык выбирается заново на каждое посещение
    return null;
  }
}

export function rememberLanguage(language: Language): void {
  try {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  } catch {
    // Записать не вышло — выбор доживёт до конца этого посещения
  }
}

/**
 * Проставить язык в разметку.
 *
 * Это не украшение: по нему браузер переносит слова, а экранный диктор
 * выбирает произношение. Русский текст, прочитанный английским голосом,
 * разобрать нельзя.
 */
export function applyLanguage(language: Language): void {
  document.documentElement.setAttribute("lang", language);
}
