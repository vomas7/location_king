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
import { useText } from "~/state/languageContext";

const KINDS: FeedbackKind[] = ["impression", "problem"];

/** Столько же принимает сервер: подсказка о длине должна совпадать с правилом. */
const MAX_LENGTH = 2000;

/** С какого остатка показывать счётчик: раньше он только мешает писать. */
const COUNTER_FROM = 200;

export function Feedback() {
  const { feedback: text } = useText();
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
      setError(text.empty);
      return;
    }

    setBusy(true);
    try {
      await feedbackApi.send(kind, message.trim());
      setSent(true);
    } catch (caught) {
      setError(errorMessage(caught, text.failed));
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
        {text.open}
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
            aria-label={text.label}
          >
            {sent ? (
              <>
                <h2 className={styles.title}>{text.sent}</h2>
                <p className={styles.text}>{text.thanks}</p>

                <div className={styles.actions}>
                  <Button type="button" variant="primary" onClick={close}>
                    {text.close}
                  </Button>
                </div>
              </>
            ) : (
              <>
                <h2 className={styles.title}>{text.title}</h2>
                <p className={styles.text}>{text.invitation}</p>

                <form className={styles.form} onSubmit={(event) => void submit(event)} noValidate>
                  <Segmented
                    label={text.about}
                    options={KINDS.map((value) => ({ value, label: text.kinds[value] }))}
                    value={kind}
                    onChange={setKind}
                  />

                  <TextArea
                    label={text.message}
                    {...(left <= COUNTER_FROM ? { hint: text.left(left) } : {})}
                    placeholder={text.hints[kind]}
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
                      {text.cancel}
                    </Button>
                    <Button type="submit" variant="primary" disabled={busy}>
                      {text.send}
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
