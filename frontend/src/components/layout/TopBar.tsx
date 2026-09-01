/** Шапка: логотип, прогресс партии и вход. */

import { Button } from "~/components/ui/Button";
import type { AvatarView } from "~/api/types";
import { Avatar } from "~/components/ui/Avatar";
import styles from "~/components/layout/TopBar.module.css";
import { useFormats, useText } from "~/state/languageContext";

interface Progress {
  roundIndex: number;
  roundsTotal: number;
  score: number;
}

interface TopBarProps {
  playerName: string | null;
  /** Аватарка игрока рядом с именем. Пусто, пока профиль не загружен. */
  playerAvatar: AvatarView | null;
  progress: Progress | null;
  onQuit?: () => void;
  onLogout: () => void;
}

/**
 * Знак игры — то же перекрестие, что стоит в центре снимка.
 *
 * Он повторяется на вкладке браузера и на карте: игрок каждый раз целится в
 * одну и ту же метку, и она же представляет игру.
 */
function Reticle() {
  return (
    <span className={styles.mark} aria-hidden="true">
      <svg viewBox="0 0 32 32" width="18" height="18" fill="none" stroke="currentColor">
        <circle cx="16" cy="16" r="6" strokeWidth="2.5" />
        <path d="M16 2v7M16 23v7M2 16h7M23 16h7" strokeWidth="2.5" strokeLinecap="round" />
      </svg>
    </span>
  );
}

/**
 * Прогресс партии показан полосками, а не только цифрами: так видно, сколько
 * осталось, не читая текст.
 */
function ProgressBar({ roundIndex, roundsTotal, score }: Progress) {
  const { topbar } = useText();
  const formats = useFormats();

  return (
    <div className={styles.progress}>
      <div className={styles.progressLine}>
        <span className={styles.progressLabel}>{topbar.round(roundIndex, roundsTotal)}</span>
        <span className={styles.progressScore}>{formats.number(score)}</span>
      </div>

      <div
        className={styles.track}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={roundsTotal}
        aria-valuenow={roundIndex - 1}
        aria-label={topbar.progress}
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

export function TopBar({ playerName, playerAvatar, progress, onQuit, onLogout }: TopBarProps) {
  const { topbar } = useText();

  return (
    <header className={styles.topbar}>
      <div className={styles.brand}>
        <Reticle />
        <span className={styles.name}>Location King</span>
      </div>

      {progress !== null && <ProgressBar {...progress} />}

      <div className={styles.user}>
        {playerName !== null && (
          <span className={styles.player}>
            {playerAvatar !== null && <Avatar avatar={playerAvatar} size={22} name={playerName} />}
            {playerName}
          </span>
        )}

        {/* Во время партии выход из игры не показываем: он стоит рядом с
            «Завершить», уводит из партии так же безвозвратно, и промах по
            нему стоит игроку всех набранных очков */}
        {onQuit === undefined ? (
          <Button variant="ghost" size="small" onClick={onLogout}>
            {topbar.logout}
          </Button>
        ) : (
          <Button variant="ghost" size="small" onClick={onQuit}>
            {topbar.quit}
          </Button>
        )}
      </div>
    </header>
  );
}
