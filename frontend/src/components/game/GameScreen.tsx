/** Экран игры: снимок во весь экран и панель с картой догадки. */

import { useCallback, useEffect, useState } from "react";

import type { RoundView } from "~/api/types";
import styles from "~/components/game/GameScreen.module.css";
import { GuessPanel } from "~/components/game/GuessPanel";
import { SatelliteView } from "~/components/game/SatelliteView";
import type { LonLat } from "~/map/guess";

interface GameScreenProps {
  round: RoundView;
  guess: LonLat | null;
  busy: boolean;
  onPick: (guess: LonLat) => void;
  onSubmit: () => void;
}

export function GameScreen({ round, guess, busy, onPick, onSubmit }: GameScreenProps) {
  const [pinned, setPinned] = useState(false);
  const [resetSignal, setResetSignal] = useState(0);

  const resetView = useCallback(() => {
    setResetSignal((value) => value + 1);
  }, []);

  // Горячие клавиши: играть одной мышью неудобно, когда карта раскрыта
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement) return;

      if (event.key === "m" || event.key === "M" || event.key === "ь") {
        setPinned((value) => !value);
        return;
      }

      if (event.key === "r" || event.key === "R" || event.key === "к") {
        resetView();
        return;
      }

      if (event.key === "Enter" && guess !== null && !busy) {
        onSubmit();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [guess, busy, onSubmit, resetView]);

  return (
    <div className={styles.screen}>
      <SatelliteView round={round} resetSignal={resetSignal} />

      <GuessPanel
        roundId={round.id}
        guess={guess}
        busy={busy}
        pinned={pinned}
        onPin={setPinned}
        onPick={onPick}
        onSubmit={onSubmit}
      />
    </div>
  );
}
