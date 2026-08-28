/**
 * Оформление интерфейса.
 *
 * Выбор хранится у игрока на сервере: он должен пережить и очистку
 * хранилища, и переход на другое устройство. В браузере лежит копия — она
 * нужна ровно затем, чтобы знать тему до ответа сервера, и её же читает
 * public/theme.js до первой отрисовки.
 */

import type { Theme } from "~/api/types";

export type { Theme };

/** Что игрок выбрал; «как в системе» — тоже выбор, а не отсутствие выбора. */
export const THEMES: { value: Theme; label: string }[] = [
  { value: "dark", label: "Тёмная" },
  { value: "light", label: "Светлая" },
  { value: "system", label: "Как в системе" },
];

/** Ключ в localStorage. Он назван в документе про хранилище, и тест это сверяет. */
export const THEME_STORAGE_KEY = "location-king:theme";

/** То же значение, что понимает public/theme.js и что стоит в разметке. */
export type ResolvedTheme = "dark" | "light";

const SYSTEM_LIGHT = "(prefers-color-scheme: light)";

export function isTheme(value: unknown): value is Theme {
  return value === "dark" || value === "light" || value === "system";
}

/** Что лежит в браузере от прошлого раза. */
export function storedTheme(): Theme {
  try {
    const raw = localStorage.getItem(THEME_STORAGE_KEY);
    return isTheme(raw) ? raw : "system";
  } catch {
    // Приватный режим: пока не приехал профиль, играем по системной
    return "system";
  }
}

export function rememberTheme(theme: Theme): void {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Записать не вышло — тема будет применяться каждый раз заново
  }
}

/**
 * Применить тему и следить за системной, пока выбрана «как в системе».
 *
 * В разметку попадает уже разрешённое значение — «dark» или «light»: так
 * светлая палитра описана в токенах один раз, а не двумя одинаковыми
 * блоками, один из которых в медиазапросе.
 *
 * Возвращает функцию, снимающую слежение.
 */
export function applyTheme(theme: Theme): () => void {
  if (theme !== "system") {
    setResolved(theme);
    return () => undefined;
  }

  const query = window.matchMedia(SYSTEM_LIGHT);
  const follow = () => {
    setResolved(query.matches ? "light" : "dark");
  };

  follow();
  query.addEventListener("change", follow);

  return () => {
    query.removeEventListener("change", follow);
  };
}

function setResolved(theme: ResolvedTheme): void {
  document.documentElement.setAttribute("data-theme", theme);
}
