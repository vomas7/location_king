/**
 * Удаление учётной записи.
 *
 * Политика конфиденциальности обещает, что данные можно стереть, — значит,
 * кнопка должна быть на виду и работать. Пароль спрашиваем ещё раз: это
 * необратимо, и случайных нажатий здесь быть не должно.
 */

import { useRef, useState, type FormEvent } from "react";

import { errorMessage } from "~/api/client";
import { auth } from "~/api/endpoints";
import styles from "~/components/home/DeleteAccount.module.css";
import { Alert } from "~/components/ui/Alert";
import { Button } from "~/components/ui/Button";
import { Field } from "~/components/ui/Field";
import { useFocusTrap } from "~/components/ui/useFocusTrap";
import { useAuth } from "~/state/authContext";

export function DeleteAccount() {
  const { logout } = useAuth();
  const dialog = useRef<HTMLDivElement>(null);

  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useFocusTrap(dialog);

  const close = () => {
    setOpen(false);
    setPassword("");
    setError(null);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);

    if (password === "") {
      setError("Введи пароль");
      return;
    }

    setBusy(true);
    try {
      await auth.deleteAccount(password);
      logout();
    } catch (caught) {
      setError(errorMessage(caught, "Не удалось удалить учётную запись"));
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
        Удалить аккаунт
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
            aria-label="Удаление учётной записи"
          >
            <h2 className={styles.title}>Удалить аккаунт?</h2>

            <p className={styles.text}>
              Вместе с ним исчезнут все партии, раунды, место в таблице лидеров и созданные тобой
              комнаты. Восстановить это будет нечем.
            </p>

            <form className={styles.form} onSubmit={(event) => void submit(event)} noValidate>
              <Field
                label="Пароль"
                type="password"
                autoComplete="current-password"
                placeholder="Подтверди, что это ты"
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value);
                }}
              />

              <Alert message={error} />

              <div className={styles.actions}>
                <Button type="button" onClick={close}>
                  Отмена
                </Button>
                <Button type="submit" variant="primary" disabled={busy}>
                  Удалить навсегда
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
