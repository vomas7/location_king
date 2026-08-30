/** Экран игры: снимок во весь экран и панель с картой догадки. */

import { useCallback, useEffect, useState } from "react";

import type { RoundView } from "~/api/types";
import { ChoicePanel } from "~/components/game/ChoicePanel";
import { FirstRoundCoach } from "~/components/game/FirstRoundCoach";
import styles from "~/components/game/GameScreen.module.css";
import { GuessPanel } from "~/components/game/GuessPanel";
import { RoundTimer } from "~/components/game/RoundTimer";
import { SatelliteView } from "~/components/game/SatelliteView";
import type { Answer } from "~/api/types";
import { useCountdown } from "~/state/useCountdown";
import { useHoverPointer } from "~/state/usePointer";

interface GameScreenProps {
  round: RoundView;
  guess: Answer | null;
  busy: boolean;
  timeLimitSeconds: number | null;
  /** Показывать ли подсказки: это первый раунд первой партии игрока. */
  coaching: boolean;
  onPick: (guess: Answer) => void;
  /** Взять подсказку по этому раунду. */
  onHint: () => void;
  onSubmit: () => void;
  /** Время вышло, а точка не поставлена. */
  onTimeout: () => void;
}

export function GameScreen({
  round,
  guess,
  busy,
  timeLimitSeconds,
  coaching,
  onPick,
  onHint,
  onSubmit,
  onTimeout,
}: GameScreenProps) {
  const [pinned, setPinned] = useState(false);
  const [resetSignal, setResetSignal] = useState(0);
  // Закрытые подсказки не возвращаются до конца партии: экран игры живёт всю
  // партию, поэтому хранить этот отказ где-то ещё незачем
  const [coachDismissed, setCoachDismissed] = useState(false);
  const { secondsLeft, expired } = useCountdown(round.deadline_at);
  const hoverPointer = useHoverPointer();

  // Мышью карта раскрывается подводом курсора, пальцем — нажатием. Знать это
  // нужно и панели, и подсказке новичка, поэтому считается здесь
  const mapOpen = pinned || hoverPointer;

  // Время вышло: отправляем поставленную точку, а если её нет — закрываем
  // раунд. Решение всё равно принимает сервер, здесь только повод его позвать.
  useEffect(() => {
    if (!expired || busy) return;

    if (guess === null) {
      onTimeout();
    } else {
      onSubmit();
    }
  }, [expired, busy, guess, onSubmit, onTimeout]);

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
      <SatelliteView round={round} resetSignal={resetSignal} onReset={resetView} />

      {coaching && !coachDismissed && (
        <FirstRoundCoach
          mapOpen={pinned}
          hasGuess={guess !== null}
          byCountry={round.answer_mode !== "point"}
          onDismiss={() => {
            setCoachDismissed(true);
          }}
        />
      )}

      {secondsLeft !== null && timeLimitSeconds !== null && (
        <RoundTimer secondsLeft={secondsLeft} totalSeconds={timeLimitSeconds} />
      )}

      {/* В режиме выбора карты нет вовсе: под снимком шесть названий */}
      {round.answer_mode === "choice" ? (
        <ChoicePanel round={round} guess={guess} busy={busy} onPick={onPick} onSubmit={onSubmit} />
      ) : (
        <GuessPanel
          round={round}
          guess={guess}
          busy={busy}
          pinned={pinned}
          open={mapOpen}
          onPin={setPinned}
          onPick={onPick}
          onHint={onHint}
          onSubmit={onSubmit}
        />
      )}
    </div>
  );
}
