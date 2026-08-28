/**
 * Публичное лицо игрока: имя и аватарка.
 *
 * И то и другое видно в таблице лидеров, в челлендже и в комнатах, поэтому
 * меняется там же, где игрок смотрит свою статистику, — а не прячется в
 * разделе настроек, которого в игре нет.
 *
 * Аватарка выбирается, а не загружается: сервер хранит два числа, узор по ним
 * рисуется на месте. Ни файлов, ни модерации, ни запросов на чужие домены.
 */

import { useState, type FormEvent } from "react";

import { errorMessage } from "~/api/client";
import { auth } from "~/api/endpoints";
import styles from "~/components/home/PublicProfile.module.css";
import { Alert } from "~/components/ui/Alert";
import { Avatar } from "~/components/ui/Avatar";
import { Button } from "~/components/ui/Button";
import { Field } from "~/components/ui/Field";
import { useAuth } from "~/state/authContext";

/** Столько же разрешает сервер: подсказка о длине должна совпадать с правилом. */
const MAX_LENGTH = 24;

/** Столько же форм и цветов знает Avatar — и столько же принимает сервер. */
const SHAPES = [0, 1, 2, 3, 4, 5];
const COLORS = [0, 1, 2, 3, 4, 5];

export function PublicProfile() {
  const { user, accept } = useAuth();

  const current = user?.display_name ?? user?.username ?? "";

  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(current);
  const [shape, setShape] = useState(user?.avatar.shape ?? 0);
  const [color, setColor] = useState(user?.avatar.color ?? 0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user === null) return null;

  const open = () => {
    setName(current);
    setShape(user.avatar.shape);
    setColor(user.avatar.color);
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

    const renamed = name.trim() !== current;
    const redrawn = shape !== user.avatar.shape || color !== user.avatar.color;

    if (!renamed && !redrawn) {
      close();
      return;
    }

    setBusy(true);
    try {
      // Отправляем только изменившееся: пустой запрос сервер отвергает, а
      // лишнее поле сбросило бы лимит на смену имени без причины
      accept(
        await auth.updateProfile({
          ...(renamed ? { display_name: name } : {}),
          ...(redrawn ? { avatar_shape: shape, avatar_color: color } : {}),
        }),
      );
      setEditing(false);
    } catch (caught) {
      setError(errorMessage(caught, "Не удалось сохранить"));
    } finally {
      setBusy(false);
    }
  };

  if (!editing) {
    return (
      <div className={styles.row}>
        <Avatar avatar={user.avatar} size={28} name={current} />
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

      <fieldset className={styles.picker}>
        <legend className={styles.pickerLabel}>Аватарка</legend>

        <div className={styles.choices} role="radiogroup" aria-label="Узор аватарки">
          {SHAPES.map((option) => (
            <button
              key={option}
              type="button"
              role="radio"
              aria-checked={option === shape}
              aria-label={`Узор ${String(option + 1)}`}
              className={[styles.choice, option === shape ? styles.choiceActive : ""]
                .filter(Boolean)
                .join(" ")}
              onClick={() => {
                setShape(option);
              }}
            >
              <Avatar avatar={{ shape: option, color }} size={34} />
            </button>
          ))}
        </div>

        <div className={styles.choices} role="radiogroup" aria-label="Цвет аватарки">
          {COLORS.map((option) => (
            <button
              key={option}
              type="button"
              role="radio"
              aria-checked={option === color}
              aria-label={`Цвет ${String(option + 1)}`}
              className={[styles.choice, option === color ? styles.choiceActive : ""]
                .filter(Boolean)
                .join(" ")}
              onClick={() => {
                setColor(option);
              }}
            >
              <Avatar avatar={{ shape, color: option }} size={34} />
            </button>
          ))}
        </div>
      </fieldset>

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
