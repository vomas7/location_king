import type { HTMLAttributes, ReactNode } from "react";

import styles from "~/components/ui/ui.module.css";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function Card({ className, children, ...rest }: CardProps) {
  return (
    <div className={[styles.card, className].filter(Boolean).join(" ")} {...rest}>
      {children}
    </div>
  );
}

export function CardTitle({ children }: { children: ReactNode }) {
  return <h2 className={styles.cardTitle}>{children}</h2>;
}

export function CardSubtitle({ children }: { children: ReactNode }) {
  return <p className={styles.cardSubtitle}>{children}</p>;
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return <p className={styles.eyebrow}>{children}</p>;
}
