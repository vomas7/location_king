import styles from "~/components/ui/ui.module.css";

/** Сообщение об ошибке. Ничего не рисует, если сообщения нет. */
export function Alert({ message }: { message: string | null }) {
  if (message === null) return null;

  return (
    <p className={styles.alert} role="alert">
      {message}
    </p>
  );
}
