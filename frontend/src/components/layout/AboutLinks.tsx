/**
 * Правовые документы, обратная связь и указание правообладателей.
 *
 * Один набор ссылок на два места: подвал посадочной страницы и раздел
 * «Профиль» в меню игры. В самом меню подвала больше нет — он занимал экран
 * телефона строками, которые открывают раз в жизни, — но выкинуть ссылки
 * нельзя: указание правообладателей это условие лицензии, а не вежливость.
 */

import type { ReactNode } from "react";

import styles from "~/components/layout/Footnotes.module.css";
import type { LegalDocumentId } from "~/legal/documents";
import { LEGAL_DOCUMENTS } from "~/legal/documents";
import { OPERATOR_EMAIL } from "~/legal/operator";
import { useText } from "~/state/languageContext";

/**
 * Где лежит игра. Адрес постоянный и публичный — как ссылка на лицензию
 * OpenStreetMap рядом, — поэтому записан здесь, а не приходит из окружения:
 * из окружения берутся только реквизиты оператора, которых нет в репозитории.
 */
const REPOSITORY_URL = "https://github.com/vomas7/location_king";

interface AboutLinksProps {
  onOpen: (document: LegalDocumentId) => void;
  /** Что ещё встаёт в ту же строку сносок: например, выбор языка. */
  children?: ReactNode;
}

/**
 * Документы, обратная связь и исходники.
 *
 * Подписи короткие — те же, что на вкладках самого документа: полное название
 * стоит в его заголовке, а в сноске из полных названий набиралось пять строк
 * подряд, и на телефоне подвал занимал половину экрана. Сетка в два столбца
 * держит их парами независимо от длины подписи и языка.
 */
export function LegalLinks({ onOpen, children }: AboutLinksProps) {
  const { footer, legal } = useText();

  return (
    <nav className={styles.links} aria-label={footer.navLabel}>
      {LEGAL_DOCUMENTS.map((document) => (
        <button
          key={document.id}
          type="button"
          className={styles.link}
          onClick={() => {
            onOpen(document.id);
          }}
        >
          {legal.tabs[document.id]}
        </button>
      ))}

      {OPERATOR_EMAIL !== "" && (
        <a className={styles.link} href={`mailto:${OPERATOR_EMAIL}`}>
          {footer.write}
        </a>
      )}

      <a className={styles.link} href={REPOSITORY_URL} target="_blank" rel="noreferrer noopener">
        {footer.source}
      </a>

      {children}
    </nav>
  );
}

/**
 * Подпись к карте. Это условие лицензии, а не ссылка в ряду прочих, поэтому
 * стоит отдельной строкой и набрана как сноска. Провайдер снимков подписан
 * прямо на экране игры: его название приходит вместе с раундом.
 */
export function Credits() {
  const { footer } = useText();

  return (
    <p className={styles.credits}>
      {footer.creditsBefore}{" "}
      <a
        className={styles.credit}
        href="https://www.openstreetmap.org/copyright"
        target="_blank"
        rel="noreferrer noopener"
      >
        OpenStreetMap
      </a>
      {footer.creditsAfter === "" ? "" : ` ${footer.creditsAfter}`}
    </p>
  );
}
