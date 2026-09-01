/**
 * Переключатель языка в подвале.
 *
 * Языков два, поэтому это не список, а одна ссылка-сноска, подписанная тем
 * языком, на который она переключит: «English» по-русски и «Русский»
 * по-английски. Подпись всегда на языке цели — её должен прочитать тот, кто
 * текущего языка не понимает.
 *
 * Стоит рядом с документами и счётчиком игроков: это сноска, а не настройка
 * игры. Свою настройку игрок найдёт в профиле, рядом с оформлением.
 */

import styles from "~/components/layout/Footnotes.module.css";
import { useLanguage } from "~/state/languageContext";

export function LanguageSwitch() {
  const { language, text, choose } = useLanguage();

  return (
    <button
      type="button"
      className={styles.link}
      lang={language === "ru" ? "en" : "ru"}
      onClick={() => {
        choose(language === "ru" ? "en" : "ru");
      }}
    >
      {text.language.switchTo}
    </button>
  );
}
