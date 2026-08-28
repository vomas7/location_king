/** Подвал посадочной страницы: документы, исходный код и правообладатели. */

import { Credits, LegalLinks } from "~/components/layout/AboutLinks";
import styles from "~/components/layout/Footer.module.css";
import type { LegalDocumentId } from "~/legal/documents";

interface FooterProps {
  onOpen: (document: LegalDocumentId) => void;
}

export function Footer({ onOpen }: FooterProps) {
  return (
    <footer className={styles.footer}>
      <LegalLinks onOpen={onOpen} />
      <Credits />
    </footer>
  );
}
