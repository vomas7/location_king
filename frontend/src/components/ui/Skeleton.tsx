/**
 * Заглушка на время загрузки.
 *
 * Карточки главного экрана приходят из разных запросов. Если прятать их до
 * ответа, разметка прыгает и экран собирается на глазах; полоски держат место
 * и показывают, что данные едут.
 */

import styles from "~/components/ui/ui.module.css";

interface SkeletonProps {
  /** Сколько строк занять. По умолчанию три — типичный список. */
  rows?: number;
}

export function Skeleton({ rows = 3 }: SkeletonProps) {
  return (
    <div className={styles.skeleton} role="status" aria-label="Загружаем">
      {Array.from({ length: rows }, (_, index) => (
        <span key={index} className={styles.skeletonRow} />
      ))}
    </div>
  );
}
