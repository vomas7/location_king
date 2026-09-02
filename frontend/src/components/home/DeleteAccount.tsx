/**
 * Удаление учётной записи.
 *
 * Политика конфиденциальности обещает, что данные можно стереть, — значит,
 * кнопка должна быть на виду и работать. Пароль спрашиваем ещё раз: это
 * необратимо, и случайных нажатий здесь быть не должно.
 */

import { useCallback, useRef, useState, type FormEvent } from "react";

import { errorMessage } from "~/api/client";
import { auth } from "~/api/endpoints";
import styles from "~/components/home/DeleteAccount.module.css";
import { Alert } from "~/components/ui/Alert";
import { Button } from "~/components/ui/Button";
import { PasswordField } from "~/components/ui/PasswordField";
import { useModal } from "~/components/ui/useModal";
import { useText } from "~/state/languageContext";
import { useAuth } from "~/state/authContext";

export function DeleteAccount() {
  const { deleteAccount: text } = useText();
  const { logout } = useAuth();
  const dialog = useRef<HTMLDivElement>(null);

  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const close = useCallback(() => {
    setOpen(false);
    setPassword("");
    setError(null);
  }, []);

  useModal(dialog, open, close);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);

    if (password === "") {
      setError(text.needPassword);
      return;
    }

    setBusy(true);
    try {
      await auth.deleteAccount(password);
      logout();
    } catch (caught) {
      setError(errorMessage(caught, text.failed));
    } finally {
      setBusy(false);
    }
  };

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
            <h2 className={styles.title}>{text.title}</h2>

            <p className={styles.text}>{text.warning}</p>

            <form className={styles.form} onSubmit={(event) => void submit(event)} noValidate>
              <PasswordField
                label={text.password}
                autoComplete="current-password"
                placeholder={text.passwordPlaceholder}
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value);
                }}
              />

              <Alert message={error} />

              <div className={styles.actions}>
                <Button type="button" onClick={close}>
                  {text.cancel}
                </Button>
                <Button type="submit" variant="primary" disabled={busy}>
                  {text.confirm}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
