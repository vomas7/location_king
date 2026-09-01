/**
 * Переключатель языка: подпись и два флага.
 *
 * Стоит наверху, потому что там его ищут: на сайтах с двумя языками флаг в
 * шапке — привычка, и искать язык в подвале или в профиле никто не станет.
 *
 * Флаг — это страна, а не язык, и строго говоря так обозначать язык неверно.
 * Но узнаётся он мгновенно и без чтения, а это ровно то, что нужно человеку,
 * который текущего языка не понимает. Поэтому рядом с флагом стоит и
 * название языка — для читалок и для тех, кому флага мало.
 */

import styles from "~/components/layout/LanguageSwitch.module.css";
import type { Language } from "~/domain/language";
import { LANGUAGES } from "~/domain/language";
import { useLanguage } from "~/state/languageContext";

/** Флаг России: три полосы, больше в нём ничего и нет. */
function RussianFlag() {
  return (
    <svg viewBox="0 0 60 30" className={styles.flag} aria-hidden="true" focusable="false">
      <rect width="60" height="10" fill="#ffffff" />
      <rect y="10" width="60" height="10" fill="#0039a6" />
      <rect y="20" width="60" height="10" fill="#d52b1e" />
    </svg>
  );
}

/**
 * Флаг Великобритании. Диагонали нарисованы линиями поверх фона: на значке в
 * двадцать пикселей разница со смещёнными по правилам геральдики полосами не
 * видна, а разметка вместо десятка многоугольников — четыре линии.
 */
function BritishFlag() {
  return (
    <svg viewBox="0 0 60 30" className={styles.flag} aria-hidden="true" focusable="false">
      <clipPath id="union-jack">
        <rect width="60" height="30" />
      </clipPath>
      <g clipPath="url(#union-jack)">
        <rect width="60" height="30" fill="#012169" />
        <path d="M0,0 L60,30 M60,0 L0,30" stroke="#ffffff" strokeWidth="6" />
        <path d="M0,0 L60,30 M60,0 L0,30" stroke="#c8102e" strokeWidth="3" />
        <path d="M30,0 V30 M0,15 H60" stroke="#ffffff" strokeWidth="10" />
        <path d="M30,0 V30 M0,15 H60" stroke="#c8102e" strokeWidth="6" />
      </g>
    </svg>
  );
}

const FLAGS: Record<Language, () => JSX.Element> = {
  ru: RussianFlag,
  en: BritishFlag,
};

export function LanguageSwitch() {
  const { language, text, choose } = useLanguage();

  return (
    <div className={styles.switch}>
      <span className={styles.label}>{text.language.label}:</span>

      <div className={styles.flags} role="group" aria-label={text.language.label}>
        {LANGUAGES.map((option) => {
          const Flag = FLAGS[option.value];
          const current = option.value === language;

          return (
            <button
              key={option.value}
              type="button"
              className={[styles.choice, current ? styles.choiceActive : ""]
                .filter(Boolean)
                .join(" ")}
              aria-label={option.label}
              aria-pressed={current}
              lang={option.value}
              onClick={() => {
                choose(option.value);
              }}
            >
              <Flag />
            </button>
          );
        })}
      </div>
    </div>
  );
}
