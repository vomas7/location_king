/**
 * Публичное лицо игрока: имя и аватарка.
 *
 * И то и другое видно в таблице лидеров, в челлендже и в комнатах, поэтому
 * меняется там же, где игрок смотрит свою статистику, — а не прячется в
 * разделе настроек, которого в игре нет.
 *
 * Аватарка бывает двух видов. Узор рисуется на месте по двум числам — он есть
 * у каждого сразу и ничего не весит. Свою картинку игрок загружает сам, и
 * тогда показывают её; узор остаётся под ней и возвращается, если картинку
 * убрать. Поэтому это не два переключателя, а одно место с двумя состояниями.
 */

import { useRef, useState, type FormEvent } from "react";

import { errorMessage } from "~/api/client";
import { auth } from "~/api/endpoints";
import styles from "~/components/home/PublicProfile.module.css";
import { Alert } from "~/components/ui/Alert";
import { Avatar } from "~/components/ui/Avatar";
import { Button } from "~/components/ui/Button";
import { Field } from "~/components/ui/Field";
import { useAuth } from "~/state/authContext";
import { useText } from "~/state/languageContext";

/** Столько же разрешает сервер: подсказка о длине должна совпадать с правилом. */
const MAX_LENGTH = 24;

/** Столько же форм и цветов знает Avatar — и столько же принимает сервер. */
const SHAPES = [0, 1, 2, 3, 4, 5];
const COLORS = [0, 1, 2, 3, 4, 5];

/** Столько же пропускает сервер. Проверяем здесь, чтобы не гнать зря мегабайты. */
const MAX_BYTES = 4 * 1024 * 1024;

export function PublicProfile() {
  const { profile: text } = useText();
  const { user, accept } = useAuth();

  const current = user?.display_name ?? user?.username ?? "";

  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(current);
  const [shape, setShape] = useState(user?.avatar.shape ?? 0);
  const [color, setColor] = useState(user?.avatar.color ?? 0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const fileInput = useRef<HTMLInputElement>(null);

  if (user === null) return null;

  const picture = user.avatar.image_url !== null;

  const upload = async (file: File) => {
    setError(null);

    if (file.size > MAX_BYTES) {
      setError(text.tooHeavy);
      return;
    }

    setBusy(true);
    try {
      // Применяется сразу, не по «Сохранить»: файл в состоянии формы держать
      // незачем, а у загрузки на сервере свой лимит
      accept(await auth.uploadAvatar(file));
    } catch (caught) {
      setError(errorMessage(caught, text.uploadFailed));
    } finally {
      setBusy(false);
    }
  };

  const dropPicture = async () => {
    setError(null);
    setBusy(true);
    try {
      accept(await auth.dropAvatar());
    } catch (caught) {
      setError(errorMessage(caught, text.removeFailed));
    } finally {
      setBusy(false);
    }
  };

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
      setError(errorMessage(caught, text.saveFailed));
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
          {text.edit}
        </button>
      </div>
    );
  }

  return (
    <form className={styles.form} onSubmit={(event) => void submit(event)} noValidate>
      <Field
        label={text.name}
        hint={text.nameHint(MAX_LENGTH)}
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
        <legend className={styles.pickerLabel}>{text.avatar}</legend>

        {/* Поле выбора файла системное и некрасивое, поэтому спрятано за
            обычной кнопкой — она же объясняет, что будет с картинкой */}
        <input
          ref={fileInput}
          type="file"
          className={styles.file}
          accept="image/jpeg,image/png,image/webp,image/gif"
          onChange={(event) => {
            const chosen = event.target.files?.[0];
            // Значение сбрасывается, иначе тот же файл второй раз подряд не
            // выберется: браузер не считает это изменением
            event.target.value = "";
            if (chosen !== undefined) void upload(chosen);
          }}
        />

        {picture ? (
          <div className={styles.uploaded}>
            <Avatar avatar={user.avatar} size={64} name={current} />
            <div className={styles.uploadedText}>
              <p className={styles.uploadedTitle}>{text.ownPicture}</p>
              <p className={styles.uploadedHint}>{text.ownPictureHint}</p>
              <div className={styles.uploadedActions}>
                <Button
                  type="button"
                  size="small"
                  disabled={busy}
                  onClick={() => fileInput.current?.click()}
                >
                  {text.replacePicture}
                </Button>
                <Button
                  type="button"
                  size="small"
                  disabled={busy}
                  onClick={() => {
                    void dropPicture();
                  }}
                >
                  {text.removePicture}
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <Button type="button" block disabled={busy} onClick={() => fileInput.current?.click()}>
            {text.uploadPicture}
          </Button>
        )}

        {!picture && (
          <div className={styles.choices} role="radiogroup" aria-label={text.patterns}>
            {SHAPES.map((option) => (
              <button
                key={option}
                type="button"
                role="radio"
                aria-checked={option === shape}
                aria-label={text.pattern(option + 1)}
                className={[styles.choice, option === shape ? styles.choiceActive : ""]
                  .filter(Boolean)
                  .join(" ")}
                onClick={() => {
                  setShape(option);
                }}
              >
                <Avatar avatar={{ shape: option, color, image_url: null }} size={34} />
              </button>
            ))}
          </div>
        )}

        {!picture && (
          <div className={styles.choices} role="radiogroup" aria-label={text.colors}>
            {COLORS.map((option) => (
              <button
                key={option}
                type="button"
                role="radio"
                aria-checked={option === color}
                aria-label={text.color(option + 1)}
                className={[styles.choice, option === color ? styles.choiceActive : ""]
                  .filter(Boolean)
                  .join(" ")}
                onClick={() => {
                  setColor(option);
                }}
              >
                <Avatar avatar={{ shape, color: option, image_url: null }} size={34} />
              </button>
            ))}
          </div>
        )}
      </fieldset>

      <Alert message={error} />

      <div className={styles.actions}>
        <Button type="button" onClick={close}>
          {text.cancel}
        </Button>
        <Button type="submit" variant="primary" disabled={busy}>
          {text.save}
        </Button>
      </div>
    </form>
  );
}
