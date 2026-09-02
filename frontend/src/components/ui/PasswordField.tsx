/**
 * Поле пароля с кнопкой «показать».
 *
 * Пароль набирают вслепую, и на телефоне это главный повод не завести
 * учётную запись: длинный пароль с заглавными и цифрами набирается с ошибкой,
 * а увидеть, где именно, нечем. Кнопка ничего не хранит и не отправляет — она
 * только меняет тип поля.
 *
 * Само поле остаётся обычным `input[type=password]`, пока игрок не нажал:
 * менеджеры паролей узнают его по типу, и подсказка «сохранить пароль»
 * работает как прежде.
 */

import { useState, type InputHTMLAttributes, type ReactNode } from "react";

import styles from "~/components/ui/ui.module.css";
import { useText } from "~/state/languageContext";

interface PasswordFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: ReactNode;
  hint?: string;
}

/** Перечёркнутый глаз означает «сейчас скрыт», обычный — «сейчас видно». */
function EyeIcon({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12Z" />
      <circle cx="12" cy="12" r="3" />
      {!open && <path d="M4 20 20 4" />}
    </svg>
  );
}

export function PasswordField({ label, hint, ...rest }: PasswordFieldProps) {
  const { auth } = useText();
  const [shown, setShown] = useState(false);

  return (
    <label className={styles.field}>
      <span className={styles.fieldLabel}>
        {label}
        {hint !== undefined && <span className={styles.fieldHint}> {hint}</span>}
      </span>

      <span className={styles.password}>
        <input className={styles.input} type={shown ? "text" : "password"} {...rest} />

        <button
          type="button"
          className={styles.reveal}
          aria-label={shown ? auth.hidePassword : auth.showPassword}
          aria-pressed={shown}
          onClick={() => {
            setShown((value) => !value);
          }}
        >
          <EyeIcon open={shown} />
        </button>
      </span>
    </label>
  );
}
