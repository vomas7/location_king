import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

import styles from "~/components/ui/ui.module.css";

type Variant = "primary" | "ghost" | "plain";
type Size = "small" | "medium" | "large";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  block?: boolean;
  children: ReactNode;
}

const VARIANTS: Record<Variant, string | undefined> = {
  primary: styles.primary,
  ghost: styles.ghost,
  plain: undefined,
};

const SIZES: Record<Size, string | undefined> = {
  small: styles.small,
  medium: undefined,
  large: styles.large,
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "plain", size = "medium", block = false, className, children, ...rest },
  ref,
) {
  const classes = [
    styles.button,
    VARIANTS[variant],
    SIZES[size],
    block ? styles.block : undefined,
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button type="button" ref={ref} className={classes} {...rest}>
      {children}
    </button>
  );
});
