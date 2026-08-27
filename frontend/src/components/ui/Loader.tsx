import styles from "~/components/ui/ui.module.css";

/** Экран ожидания поверх интерфейса. */
export function Loader({ text }: { text: string }) {
  return (
    <div className={styles.loader} role="status" aria-live="polite">
      <div className={styles.orbit} aria-hidden="true">
        <span />
      </div>
      <p className={styles.loaderText}>{text}</p>
    </div>
  );
}
