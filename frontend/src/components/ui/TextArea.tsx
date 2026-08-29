import type { ReactNode, TextareaHTMLAttributes } from "react";

import styles from "~/components/ui/ui.module.css";

interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: ReactNode;
  hint?: string;
}

/** Поле для нескольких строк. Всё как у Field, кроме высоты. */
export function TextArea({ label, hint, ...rest }: TextAreaProps) {
  return (
    <label className={styles.field}>
      <span className={styles.fieldLabel}>
        {label}
        {hint !== undefined && <span className={styles.fieldHint}> {hint}</span>}
      </span>
      <textarea className={[styles.input, styles.textarea].join(" ")} {...rest} />
    </label>
  );
}
