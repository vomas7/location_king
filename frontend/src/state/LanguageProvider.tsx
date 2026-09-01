/** Провайдер языка: словарь, форматы и переключение. */

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { formats } from "~/domain/format";
import type { Language } from "~/domain/language";
import { applyLanguage, initialLanguage, rememberLanguage } from "~/domain/language";
import { DICTIONARIES } from "~/i18n/dictionary";
import { LanguageContext } from "~/state/languageContext";

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(initialLanguage);

  useEffect(() => {
    applyLanguage(language);
  }, [language]);

  const choose = useCallback((next: Language) => {
    setLanguage(next);
    rememberLanguage(next);
  }, []);

  const value = useMemo(
    () => ({ language, text: DICTIONARIES[language], formats: formats(language), choose }),
    [language, choose],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}
