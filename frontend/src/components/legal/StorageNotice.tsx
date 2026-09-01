/**
 * Уведомление о том, что игра держит в браузере.
 *
 * Это не окно согласия: соглашаться не на что — аналитики и рекламы здесь
 * нет, а токен входа хранится ровно потому, что игрок сам попросил его
 * запомнить. Поэтому полоска ничего не блокирует и закрывается насовсем.
 */

import { useState } from "react";

import styles from "~/components/legal/StorageNotice.module.css";
import { Button } from "~/components/ui/Button";
import { useText } from "~/state/languageContext";

/** Ключ в localStorage. Он назван в документе про хранилище, и тест это сверяет. */
export const NOTICE_STORAGE_KEY = "location-king:notice";

function wasDismissed(): boolean {
  try {
    return localStorage.getItem(NOTICE_STORAGE_KEY) !== null;
  } catch {
    // Приватный режим: покажем ещё раз, это не страшно
    return false;
  }
}

interface StorageNoticeProps {
  onDetails: () => void;
}

export function StorageNotice({ onDetails }: StorageNoticeProps) {
  const { notice } = useText();
  const [hidden, setHidden] = useState(wasDismissed);

  if (hidden) return null;

  const dismiss = () => {
    setHidden(true);
    try {
      localStorage.setItem(NOTICE_STORAGE_KEY, "1");
    } catch {
      // Не записалось — полоска вернётся в следующий раз, и только
    }
  };

  return (
    <aside className={styles.notice} role="note" aria-label={notice.label}>
      <p className={styles.text}>{notice.text}</p>

      <div className={styles.actions}>
        <button type="button" className={styles.details} onClick={onDetails}>
          {notice.details}
        </button>
        <Button size="small" onClick={dismiss}>
          {notice.ok}
        </Button>
      </div>
    </aside>
  );
}
