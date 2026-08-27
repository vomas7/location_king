import type { InputHTMLAttributes, ReactNode } from "react";

import styles from "~/components/ui/ui.module.css";

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: ReactNode;
  hint?: string;
}

export function Field({ label, hint, ...rest }: FieldProps) {
  return (
    <label className={styles.field}>
      <span className={styles.fieldLabel}>
        {label}
        {hint !== undefined && <span className={styles.fieldHint}> {hint}</span>}
      </span>
      <input className={styles.input} {...rest} />
    </label>
  );
}
