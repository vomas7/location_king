/** Контекст языка интерфейса. Провайдер — в LanguageProvider.tsx. */

import { createContext, useContext } from "react";

import type { Formats } from "~/domain/format";
import type { Language } from "~/domain/language";
import type { Dictionary } from "~/i18n/dictionary";

export interface LanguageContextValue {
  language: Language;
  /** Все тексты интерфейса на выбранном языке. */
  text: Dictionary;
  /** Числа, расстояния и даты по правилам выбранного языка. */
  formats: Formats;
  choose: (language: Language) => void;
}

export const LanguageContext = createContext<LanguageContextValue | null>(null);

function useCurrent(): LanguageContextValue {
  const current = useContext(LanguageContext);

  if (current === null) {
    throw new Error("Обращение к языку вне LanguageProvider");
  }

  return current;
}

/** Тексты интерфейса. Самое частое обращение, поэтому у него короткое имя. */
export function useText(): Dictionary {
  return useCurrent().text;
}

export function useFormats(): Formats {
  return useCurrent().formats;
}

/** Выбранный язык и переключение. Нужно только самому переключателю. */
export function useLanguage(): LanguageContextValue {
  return useCurrent();
}
