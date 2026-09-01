/**
 * Шесть названий вместо карты.
 *
 * Самый простой способ ответить: карты нет вовсе, под снимком список стран,
 * и одна из них верная. Так игра начинается для тех, кто по карте пока не
 * ориентируется — узнать из списка проще, чем найти самому.
 *
 * Панель у себя ничего не решает: какие варианты показать и какой из них
 * верный, знает сервер, а порядок он перемешал ещё при сборке серии.
 */

import type { Answer, RoundView } from "~/api/types";
import styles from "~/components/game/GameScreen.module.css";
import { Button } from "~/components/ui/Button";
import { useText } from "~/state/languageContext";

interface ChoicePanelProps {
  round: RoundView;
  guess: Answer | null;
  busy: boolean;
  onPick: (guess: Answer) => void;
  onSubmit: () => void;
}

export function ChoicePanel({ round, guess, busy, onPick, onSubmit }: ChoicePanelProps) {
  const { game: text } = useText();
  const chosen = guess !== null && guess.kind === "country" ? guess.code : null;

  return (
    <div className={`${styles.panel} ${styles.choicePanel}`}>
      <div className={styles.choices} role="radiogroup" aria-label={text.choicesLabel}>
        {round.choices.map((choice) => (
          <button
            key={choice.code}
            type="button"
            role="radio"
            aria-checked={choice.code === chosen}
            className={[styles.choice, choice.code === chosen ? styles.choiceActive : ""]
              .filter(Boolean)
              .join(" ")}
            disabled={busy}
            onClick={() => {
              onPick({ kind: "country", code: choice.code, name: choice.name });
            }}
          >
            {choice.name}
          </button>
        ))}
      </div>

      <div className={styles.actions}>
        <p className={styles.hint}>{chosen === null ? text.whichCountry : text.mayChange}</p>
        <Button variant="primary" block disabled={guess === null || busy} onClick={onSubmit}>
          {text.answer}
        </Button>
      </div>
    </div>
  );
}
