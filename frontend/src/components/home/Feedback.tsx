/**
 * Обратная связь.
 *
 * Отзыв — редкое действие, поэтому в разделе он одной строкой, а форма
 * открывается в диалоге: разложенная прямо в профиле, она занимала бы экран
 * ради того, что делают раз в жизни.
 *
 * Вид отзыва спрашиваем сразу: впечатление читают, когда есть время, а
 * проблему — когда её чинят, и разбирать одно от другого глазами по тексту
 * значит однажды пропустить вторую.
 */

import { useCallback, useRef, useState, type FormEvent } from "react";

import { errorMessage } from "~/api/client";
import { feedback as feedbackApi } from "~/api/endpoints";
import type { FeedbackKind } from "~/api/types";
import styles from "~/components/home/Feedback.module.css";
import { Alert } from "~/components/ui/Alert";
import { Button } from "~/components/ui/Button";
import { Segmented } from "~/components/ui/Segmented";
import { TextArea } from "~/components/ui/TextArea";
import { useModal } from "~/components/ui/useModal";

const KINDS: { value: FeedbackKind; label: string }[] = [
  { value: "impression", label: "Впечатление" },
  { value: "problem", label: "Проблема" },
];

/** Столько же принимает сервер: подсказка о длине должна совпадать с правилом. */
const MAX_LENGTH = 2000;

/** С какого остатка показывать счётчик: раньше он только мешает писать. */
const COUNTER_FROM = 200;

const PLACEHOLDERS: Record<FeedbackKind, string> = {
  impression: "Что понравилось, а что нет",
  problem: "Что случилось и на каком экране",
};

export function Feedback() {
  const dialog = useRef<HTMLDivElement>(null);

  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<FeedbackKind>("impression");
  const [message, setMessage] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const close = useCallback(() => {
    setOpen(false);
    setMessage("");
    setSent(false);
    setError(null);
  }, []);

  useModal(dialog, open, close);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);

    if (message.trim() === "") {
      setError("Напиши, что случилось");
      return;
    }

    setBusy(true);
    try {
      await feedbackApi.send(kind, message.trim());
      setSent(true);
    } catch (caught) {
      setError(errorMessage(caught, "Не удалось отправить"));
    } finally {
      setBusy(false);
    }
  };

  const left = MAX_LENGTH - message.length;

  return (
    <>
      <button
        type="button"
        className={styles.trigger}
        onClick={() => {
          setOpen(true);
        }}
      >
        Отзыв об игре
      </button>

      {open && (
        <div
          className={styles.overlay}
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) close();
          }}
        >
          <div
            ref={dialog}
            className={styles.sheet}
            role="dialog"
            aria-modal="true"
            aria-label="Отзыв об игре"
          >
            {sent ? (
              <>
                <h2 className={styles.title}>Дошло, спасибо</h2>
                <p className={styles.text}>
                  Прочитаю всё. Ответить лично не обещаю, но чинить и делать буду именно по таким
                  письмам.
                </p>

                <div className={styles.actions}>
                  <Button type="button" variant="primary" onClick={close}>
                    Закрыть
                  </Button>
                </div>
              </>
            ) : (
              <>
                <h2 className={styles.title}>Как тебе игра?</h2>
                <p className={styles.text}>
                  Пиши прямо: что понравилось, что раздражает, что не работает.
                </p>

                <form className={styles.form} onSubmit={(event) => void submit(event)} noValidate>
                  <Segmented label="О чём" options={KINDS} value={kind} onChange={setKind} />

                  <TextArea
                    label="Сообщение"
                    {...(left <= COUNTER_FROM ? { hint: `осталось ${String(left)}` } : {})}
                    placeholder={PLACEHOLDERS[kind]}
                    value={message}
                    maxLength={MAX_LENGTH}
                    autoFocus
                    onChange={(event) => {
                      setMessage(event.target.value);
                    }}
                  />

                  <Alert message={error} />

                  <div className={styles.actions}>
                    <Button type="button" onClick={close}>
                      Отмена
                    </Button>
                    <Button type="submit" variant="primary" disabled={busy}>
                      Отправить
                    </Button>
                  </div>
                </form>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
