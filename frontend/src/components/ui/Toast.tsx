import styles from "~/components/ui/ui.module.css";

/** Короткое сообщение поверх интерфейса. */
export function Toast({ message }: { message: string }) {
  return (
    <div className={styles.toast} role="status" aria-live="polite">
      {message}
    </div>
  );
}
