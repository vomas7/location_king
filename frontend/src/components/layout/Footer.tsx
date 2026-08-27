/** Подвал: правовые документы и указание правообладателей. */

import styles from "~/components/layout/Footer.module.css";
import type { LegalDocumentId } from "~/legal/documents";
import { LEGAL_DOCUMENTS } from "~/legal/documents";
import { OPERATOR_EMAIL } from "~/legal/operator";

interface FooterProps {
  onOpen: (document: LegalDocumentId) => void;
}

export function Footer({ onOpen }: FooterProps) {
  return (
    <footer className={styles.footer}>
      <nav className={styles.links} aria-label="Правовые документы">
        {LEGAL_DOCUMENTS.map((document) => (
          <button
            key={document.id}
            type="button"
            className={styles.link}
            onClick={() => {
              onOpen(document.id);
            }}
          >
            {document.title}
          </button>
        ))}

        {OPERATOR_EMAIL !== "" && (
          <a className={styles.link} href={`mailto:${OPERATOR_EMAIL}`}>
            Написать нам
          </a>
        )}
      </nav>

      {/* Указание правообладателей — условие лицензий, а не вежливость.
          Провайдер снимков подписан прямо на экране игры: его название
          приходит вместе с раундом */}
      <p className={styles.credits}>
        Карта — © участники{" "}
        <a
          className={styles.credit}
          href="https://www.openstreetmap.org/copyright"
          target="_blank"
          rel="noreferrer noopener"
        >
          OpenStreetMap
        </a>
      </p>
    </footer>
  );
}
