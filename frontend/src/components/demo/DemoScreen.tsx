/**
 * Знакомство с игрой без учётной записи.
 *
 * Экран игры здесь тот же самый: он разбирает раунд по answer_mode и не
 * знает, что перед ним гость. Своё здесь только плашка про режим — она и есть
 * то, ради чего экскурсия устроена лесенкой: три раунда из списка, потом
 * карта стран, потом точка, и на каждом переходе меняется ровно одно.
 */

import { useEffect } from "react";

import { GameScreen } from "~/components/game/GameScreen";
import { RoundResult } from "~/components/game/RoundResult";
import styles from "~/components/demo/DemoScreen.module.css";
import { DemoFinish } from "~/components/demo/DemoFinish";
import { Loader } from "~/components/ui/Loader";
import { useText } from "~/state/languageContext";
import { useDemo } from "~/state/useDemo";

interface DemoScreenProps {
  /** Уйти из знакомства: обратно на посадочную страницу. */
  onLeave: () => void;
  /** Открыть форму регистрации. */
  onSignUp: () => void;
}

export function DemoScreen({ onLeave, onSignUp }: DemoScreenProps) {
  const { demo: text } = useText();
  const controller = useDemo();
  const { state, round } = controller;

  // Раунды приезжают один раз при появлении экрана: до этого показывать
  // нечего, а спрашивать разрешения не у кого
  const { start } = controller;
  useEffect(() => {
    void start();
  }, [start]);

  if (state.phase === "idle" || state.phase === "loading") {
    return <Loader text={state.error ?? text.loading} />;
  }

  if (state.phase === "finished") {
    return (
      <DemoFinish
        score={controller.totalScore}
        results={state.results}
        onSignUp={onSignUp}
        onAgain={() => {
          void controller.start();
        }}
        onLeave={onLeave}
      />
    );
  }

  return (
    <div className={styles.stage}>
      {round !== null && (
        <>
          {/* Плашка стоит слева сверху: справа приборы снимка, снизу слева
              масштаб и подпись источника — свободен только этот угол */}
          <div className={styles.mode}>
            <p className={styles.counter}>{text.roundOf(round.index, state.rounds.length)}</p>
            <p className={styles.modeTitle}>{modeTitle(round.answer_mode, text)}</p>
            <p className={styles.modeNote}>{modeNote(round.answer_mode, text)}</p>

            <button
              type="button"
              className={styles.leave}
              onClick={() => {
                if (window.confirm(text.leaveConfirm)) onLeave();
              }}
            >
              {text.leave}
            </button>
          </div>

          <GameScreen
            round={round}
            guess={state.guess}
            busy={state.phase !== "playing"}
            timeLimitSeconds={null}
            // Объясняет плашка режима: две карточки поверх снимка на 390
            // пикселях не помещаются, а спорить друг с другом успевают
            coaching={false}
            onPick={controller.pick}
            onHint={() => undefined}
            onSubmit={() => {
              void controller.submit();
            }}
            onTimeout={() => undefined}
          />
        </>
      )}

      {state.phase === "result" && state.lastResult !== null && (
        <RoundResult
          result={state.lastResult}
          isLastRound={controller.isLastRound}
          onNext={controller.advance}
        />
      )}
    </div>
  );
}

type DemoText = ReturnType<typeof useText>["demo"];

/** Как называется то, чем отвечают в этом раунде. */
function modeTitle(mode: string, text: DemoText): string {
  if (mode === "choice") return text.modeChoice;
  if (mode === "country") return text.modeCountry;
  return text.modePoint;
}

/** Что именно делать в этом режиме. */
function modeNote(mode: string, text: DemoText): string {
  if (mode === "choice") return text.modeChoiceNote;
  if (mode === "country") return text.modeCountryNote;
  return text.modePointNote;
}
