import type { InputHTMLAttributes, ReactNode } from "react";

import styles from "~/components/ui/ui.module.css";

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  children: ReactNode;
}

export function Checkbox({ children, ...rest }: CheckboxProps) {
  return (
    <label className={styles.checkbox}>
      <input className={styles.checkboxInput} type="checkbox" {...rest} />
      <span className={styles.checkboxText}>{children}</span>
    </label>
  );
}
