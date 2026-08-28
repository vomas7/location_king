/**
 * Смена публичного имени.
 *
 * Имя видно в таблице лидеров, в челлендже и в комнатах, поэтому меняется
 * там же, где игрок смотрит свою статистику, — а не прячется в отдельном
 * разделе настроек, которого в игре нет.
 */

import { useState, type FormEvent } from "react";

import { ApiError } from "~/api/client";
import { auth } from "~/api/endpoints";
import styles from "~/components/home/DisplayName.module.css";
import { Alert } from "~/components/ui/Alert";
import { Button } from "~/components/ui/Button";
import { Field } from "~/components/ui/Field";
import { useAuth } from "~/state/authContext";

/** Столько же разрешает сервер: подсказка о длине должна совпадать с правилом. */
const MAX_LENGTH = 24;

export function DisplayName() {
  const { user, accept } = useAuth();

  const current = user?.display_name ?? user?.username ?? "";

  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(current);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user === null) return null;

  const open = () => {
    setName(current);
    setError(null);
    setEditing(true);
  };

  const close = () => {
    setEditing(false);
    setError(null);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);

    if (name.trim() === current) {
      close();
      return;
    }

    setBusy(true);
    try {
      accept(await auth.rename(name));
      setEditing(false);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Не удалось сменить имя");
    } finally {
      setBusy(false);
    }
  };

  if (!editing) {
    return (
      <div className={styles.row}>
        <span className={styles.label}>Имя в таблице</span>
        <span className={styles.value}>{current}</span>
        <button type="button" className={styles.trigger} onClick={open}>
          Изменить
        </button>
      </div>
    );
  }

  return (
    <form className={styles.form} onSubmit={(event) => void submit(event)} noValidate>
      <Field
        label="Имя в таблице"
        hint={`его видят другие игроки, до ${String(MAX_LENGTH)} символов`}
        value={name}
        maxLength={MAX_LENGTH}
        autoComplete="nickname"
        autoFocus
        onChange={(event) => {
          setName(event.target.value);
        }}
        onKeyDown={(event) => {
          if (event.key === "Escape") close();
        }}
      />

      <Alert message={error} />

      <div className={styles.actions}>
        <Button type="button" onClick={close}>
          Отмена
        </Button>
        <Button type="submit" variant="primary" disabled={busy}>
          Сохранить
        </Button>
      </div>
    </form>
  );
}
