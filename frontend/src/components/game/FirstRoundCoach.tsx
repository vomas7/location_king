/**
 * Подсказки первого раунда.
 *
 * Показываются только тому, кто ещё не закончил ни одной партии, и только в
 * первом раунде: дальше человек уже знает, что делать, и висящая на снимке
 * карточка ему только мешает.
 */

import { useState } from "react";

import styles from "~/components/game/FirstRoundCoach.module.css";
import { Button } from "~/components/ui/Button";
import type { CoachStep } from "~/domain/onboarding";
import { coachStep } from "~/domain/onboarding";
import { useHoverPointer } from "~/state/usePointer";
import type { Dictionary } from "~/i18n/dictionary";
import { useText } from "~/state/languageContext";

interface CoachText {
  order: number;
  title: string;
  text: string;
}

const ORDER: CoachStep[] = ["look", "map", "answer"];

/**
 * Тексты шагов. Второй зависит от устройства: на телефоне карта открывается
 * кнопкой, а «подведи курсор» там — совет в пустоту. Второй и третий зависят
 * ещё и от режима: в раунде про страны точку никуда не ставят, и обещать за
 * неё очки было бы враньём, а в простом режиме нет и карты.
 */
function texts(
  hoverPointer: boolean,
  mode: string,
  text: Dictionary,
): Record<CoachStep, CoachText> {
  const coach = text.game.coach;
  const look = { order: 1, title: coach.lookTitle, text: coach.lookText };

  // В простом режиме карты нет вовсе: объяснять нечего, кроме самого списка
  if (mode === "choice") {
    return {
      look,
      map: { order: 2, title: coach.chooseTitle, text: coach.chooseText },
      answer: { order: 3, title: coach.answerTitle, text: coach.chooseAnswer },
    };
  }

  const byCountry = mode === "country";

  return {
    look,
    map: {
      order: 2,
      title: byCountry ? coach.chooseTitle : coach.pinTitle,
      text: byCountry
        ? hoverPointer
          ? coach.countryHover
          : coach.countryTap
        : hoverPointer
          ? coach.pinHover
          : coach.pinTap,
    },
    answer: {
      order: 3,
      title: coach.answerTitle,
      text: byCountry ? coach.answerCountry : coach.answerPin,
    },
  };
}

interface FirstRoundCoachProps {
  /**
   * Раскрыл ли карту сам игрок. Именно раскрыл, а не «карта видна»: мышью она
   * раскрывается наведением, и на компьютере второй шаг — как раз про то,
   * что курсор нужно к ней подвести.
   */
  mapOpen: boolean;
  /** Поставлена ли точка на карте мира или выбрана страна. */
  hasGuess: boolean;
  /** Чем отвечают: и просят разное, и очки считаются по-разному. */
  mode: string;
  /** Закрыть подсказки до конца партии. */
  onDismiss: () => void;
}

export function FirstRoundCoach({ mapOpen, hasGuess, mode, onDismiss }: FirstRoundCoachProps) {
  const text = useText();
  const [acknowledged, setAcknowledged] = useState(false);
  const hoverPointer = useHoverPointer();

  const step = coachStep(acknowledged, mapOpen, hasGuess);
  const { order, title, text: step_text } = texts(hoverPointer, mode, text)[step];

  return (
    <aside className={styles.coach} aria-live="polite">
      <p className={styles.counter}>{text.game.coachStep(order, ORDER.length)}</p>
      <h2 className={styles.title}>{title}</h2>
      <p className={styles.text}>{step_text}</p>

      <div className={styles.actions}>
        {step === "look" && (
          <Button
            variant="primary"
            size="small"
            onClick={() => {
              setAcknowledged(true);
            }}
          >
            {text.game.coachGot}
          </Button>
        )}

        <button type="button" className={styles.skip} onClick={onDismiss}>
          {text.game.coachSkip}
        </button>
      </div>
    </aside>
  );
}
