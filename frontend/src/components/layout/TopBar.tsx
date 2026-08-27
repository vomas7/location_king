/** Шапка: логотип, прогресс партии и вход. */

import { Button } from "~/components/ui/Button";
import styles from "~/components/layout/TopBar.module.css";
import { formatNumber } from "~/domain/format";

interface Progress {
  roundIndex: number;
  roundsTotal: number;
  score: number;
}

interface TopBarProps {
  playerName: string | null;
  progress: Progress | null;
  onQuit?: () => void;
  onLogout: () => void;
}

/**
 * Прогресс партии показан полосками, а не только цифрами: так видно, сколько
 * осталось, не читая текст.
 */
function ProgressBar({ roundIndex, roundsTotal, score }: Progress) {
  return (
    <div className={styles.progress}>
      <div className={styles.progressLine}>
        <span className={styles.progressLabel}>
          Раунд {roundIndex} из {roundsTotal}
        </span>
        <span className={styles.progressScore}>{formatNumber(score)}</span>
      </div>

      <div
        className={styles.track}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={roundsTotal}
        aria-valuenow={roundIndex - 1}
        aria-label="Прогресс партии"
      >
        {Array.from({ length: roundsTotal }, (_, index) => (
          <span
            key={index}
            className={[
              styles.segment,
              index < roundIndex - 1 ? styles.segmentDone : "",
              index === roundIndex - 1 ? styles.segmentCurrent : "",
            ]
              .filter(Boolean)
              .join(" ")}
          />
        ))}
      </div>
    </div>
  );
}

export function TopBar({ playerName, progress, onQuit, onLogout }: TopBarProps) {
  return (
    <header className={styles.topbar}>
      <div className={styles.brand}>
        <span className={styles.mark}>LK</span>
        <span className={styles.name}>Location King</span>
      </div>

      {progress !== null && <ProgressBar {...progress} />}

      <div className={styles.user}>
        {playerName !== null && <span className={styles.player}>{playerName}</span>}

        {onQuit !== undefined && (
          <Button variant="ghost" size="small" onClick={onQuit}>
            Завершить
          </Button>
        )}

        <Button variant="ghost" size="small" onClick={onLogout}>
          Выйти
        </Button>
      </div>
    </header>
  );
}
