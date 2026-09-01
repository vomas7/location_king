/**
 * Правовые документы: условия, политика и хранилище браузера.
 *
 * Все три живут в одном окне с вкладками, а не на отдельных страницах:
 * роутера в игре нет, а читают их обычно по ссылке из футера и сразу
 * закрывают.
 */

import { useEffect, useRef, useState } from "react";

import styles from "~/components/legal/LegalDialog.module.css";
import { Button } from "~/components/ui/Button";
import { useModal } from "~/components/ui/useModal";
import { LEGAL_DOCUMENTS, legalDocument, type LegalDocumentId } from "~/legal/documents";
import { useText } from "~/state/languageContext";

interface LegalDialogProps {
  /** Какой документ открыть. null — окно закрыто. */
  open: LegalDocumentId | null;
  onClose: () => void;
}

export function LegalDialog({ open, onClose }: LegalDialogProps) {
  const { legal } = useText();
  const dialog = useRef<HTMLDivElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const body = useRef<HTMLDivElement>(null);
  const activeTab = useRef<HTMLButtonElement>(null);
  const [current, setCurrent] = useState<LegalDocumentId>("terms");

  useModal(dialog, open !== null, onClose);

  useEffect(() => {
    if (open === null) return;

    setCurrent(open);
    closeButton.current?.focus();
  }, [open]);

  // Смена вкладки — новый текст: возвращаем чтение к началу. Заодно
  // подтягиваем саму вкладку в видимую часть: на узком экране их ряд
  // прокручивается вбок, и открытая могла оказаться за краем
  useEffect(() => {
    body.current?.scrollTo({ top: 0 });
    activeTab.current?.scrollIntoView({ inline: "center", block: "nearest" });
  }, [current]);

  if (open === null) return null;

  const document = legalDocument(current);

  return (
    <div
      className={styles.overlay}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialog}
        className={styles.sheet}
        role="dialog"
        aria-modal="true"
        aria-label={document.title}
      >
        <header className={styles.header}>
          <div className={styles.tabs} role="tablist" aria-label={legal.list}>
            {LEGAL_DOCUMENTS.map((item) => (
              <button
                key={item.id}
                ref={item.id === current ? activeTab : null}
                type="button"
                role="tab"
                aria-selected={item.id === current}
                className={[styles.tab, item.id === current ? styles.tabActive : ""]
                  .filter(Boolean)
                  .join(" ")}
                onClick={() => {
                  setCurrent(item.id);
                }}
              >
                {legal.tabs[item.id]}
              </button>
            ))}
          </div>

          <Button ref={closeButton} variant="ghost" size="small" onClick={onClose}>
            {legal.close}
          </Button>
        </header>

        <div className={styles.body} ref={body} tabIndex={0}>
          <h2 className={styles.title}>{document.title}</h2>
          <p className={styles.updated}>{legal.revision(document.updated)}</p>

          {/* Документы существуют только по-русски: сказать об этом честнее,
              чем показать англоязычному игроку страницу, которую он не ждал */}
          {legal.russianOnly !== "" && (
            <p className={styles.updated} lang="en">
              {legal.russianOnly}
            </p>
          )}

          {document.sections.map((section) => (
            <section key={section.heading} className={styles.section}>
              <h3 className={styles.heading}>{section.heading}</h3>

              {section.paragraphs?.map((text) => (
                <p key={text} className={styles.text}>
                  {text}
                </p>
              ))}

              {section.list !== undefined && (
                <ul className={styles.list}>
                  {section.list.map((item) => (
                    <li key={item} className={styles.item}>
                      {item}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
