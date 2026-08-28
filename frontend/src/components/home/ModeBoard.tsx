/**
 * Выбор режима — четыре плитки вместо четырёх карточек подряд.
 *
 * Раскрыт всегда ровно один режим: на телефоне четыре развёрнутые карточки
 * складывались в экран, который приходилось листать, чтобы просто начать
 * партию. Плитка при этом не пустая — она несёт то, ради чего в режим
 * заходят: сколько человек ищет соперника, сыгран ли сегодня челлендж.
 */

import styles from "~/components/home/ModeBoard.module.css";

export type ModeKey = "solo" | "daily" | "duel" | "room";

export interface Mode {
  key: ModeKey;
  name: string;
  /** Строка под названием: состояние режима прямо сейчас. */
  status: string;
  /** Режим ждёт действия игрока — рядом со статусом загорается точка. */
  live: boolean;
}

interface ModeBoardProps {
  modes: Mode[];
  active: ModeKey;
  onPick: (mode: ModeKey) => void;
}

export function ModeBoard({ modes, active, onPick }: ModeBoardProps) {
  return (
    <div className={styles.board} role="tablist" aria-label="Режим игры">
      {modes.map((mode) => (
        <button
          key={mode.key}
          type="button"
          role="tab"
          id={`mode-${mode.key}`}
          aria-selected={mode.key === active}
          aria-controls="mode-panel"
          className={[styles.tile, mode.key === active ? styles.tileActive : ""]
            .filter(Boolean)
            .join(" ")}
          onClick={() => {
            onPick(mode.key);
          }}
        >
          <span className={styles.name}>{mode.name}</span>
          <span className={styles.status}>
            {mode.live && <span className={styles.dot} aria-hidden="true" />}
            {mode.status}
          </span>
        </button>
      ))}
    </div>
  );
}
