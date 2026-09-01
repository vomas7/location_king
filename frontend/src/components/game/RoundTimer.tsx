/** Обратный отсчёт до конца раунда. */

import styles from "~/components/game/RoundTimer.module.css";
import { useText } from "~/state/languageContext";

interface RoundTimerProps {
  secondsLeft: number;
  totalSeconds: number;
}

/** Ниже этих порогов таймер меняет цвет. */
const WARNING_FRACTION = 0.4;
const DANGER_FRACTION = 0.15;

function formatClock(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${String(minutes)}:${String(rest).padStart(2, "0")}`;
}

export function RoundTimer({ secondsLeft, totalSeconds }: RoundTimerProps) {
  const { game: text } = useText();
  const fraction = totalSeconds > 0 ? secondsLeft / totalSeconds : 0;

  const tone =
    fraction <= DANGER_FRACTION ? "danger" : fraction <= WARNING_FRACTION ? "warning" : "normal";

  return (
    <div className={styles.timer} role="timer" aria-label={text.secondsLeft(secondsLeft)}>
      <span
        className={[
          styles.value,
          tone === "warning" ? styles.warning : "",
          tone === "danger" ? styles.danger : "",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        {formatClock(secondsLeft)}
      </span>

      <span className={styles.bar}>
        <span
          className={[
            styles.fill,
            tone === "warning" ? styles.fillWarning : "",
            tone === "danger" ? styles.fillDanger : "",
          ]
            .filter(Boolean)
            .join(" ")}
          style={{ width: `${String(fraction * 100)}%` }}
        />
      </span>
    </div>
  );
}
