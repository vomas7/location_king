/**
 * Отрисовка компонента в тестах вместе с языком.
 *
 * Любой компонент с текстом читает словарь из контекста, и без провайдера он
 * падает — намеренно: пустой текст на экране заметить труднее, чем ошибку.
 * Тесты проверяют русский интерфейс, он же язык по умолчанию.
 */

import { render, type RenderResult } from "@testing-library/react";
import type { ReactElement } from "react";

import { LANGUAGE_STORAGE_KEY } from "~/domain/language";
import { LanguageProvider } from "~/state/LanguageProvider";

export function renderWithLanguage(ui: ReactElement): RenderResult {
  // Язык выбирается по браузеру, а в jsdom он английский. Тесты проверяют
  // русский интерфейс, поэтому выбор ставится явно — тем же способом, каким
  // его делает игрок
  localStorage.setItem(LANGUAGE_STORAGE_KEY, "ru");

  // Через wrapper, а не оборачиванием вручную: тогда и rerender в тесте
  // остаётся внутри провайдера
  return render(ui, { wrapper: LanguageProvider });
}
