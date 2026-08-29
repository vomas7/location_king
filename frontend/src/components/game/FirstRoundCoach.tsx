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
 * неё очки было бы враньём.
 */
function texts(hoverPointer: boolean, byCountry: boolean): Record<CoachStep, CoachText> {
  return {
    look: {
      order: 1,
      title: "Осмотрись",
      text: "Это участок спутниковой съёмки без подписей и указателей. Крестик в центре — то самое место, которое нужно найти. Приближай колесом или щипком, тащи, чтобы осмотреть окрестности.",
    },
    map: {
      order: 2,
      title: byCountry ? "Выбери страну" : "Отметь место",
      text: byCountry
        ? hoverPointer
          ? "Подведи курсор к карте мира в правом нижнем углу и нажми на страну, из которой, по-твоему, этот снимок. Страна под курсором подсвечивается."
          : "Нажми «Выбрать страну» внизу и ткни на карте мира в страну, из которой, по-твоему, этот снимок."
        : hoverPointer
          ? "Подведи курсор к карте мира в правом нижнем углу и нажми там, где, по-твоему, снят этот участок."
          : "Нажми «Открыть карту» внизу и отметь на карте мира место, где, по-твоему, снят этот участок.",
    },
    answer: {
      order: 3,
      title: "Отвечай",
      text: byCountry
        ? "Страну можно менять сколько угодно, пока не нажал «Ответить». Угадал — все пять тысяч очков за раунд, как бы далеко от центра страны ты ни ткнул."
        : "Точку можно двигать сколько угодно, пока не нажал «Ответить». Чем ближе она к центру участка, тем больше очков — до пяти тысяч за раунд.",
    },
  };
}

interface FirstRoundCoachProps {
  /** Поставлена ли точка на карте мира или выбрана страна. */
  hasGuess: boolean;
  /** Раунд про страны: и просят другое, и очки считаются иначе. */
  byCountry: boolean;
  /** Закрыть подсказки до конца партии. */
  onDismiss: () => void;
}

export function FirstRoundCoach({ hasGuess, byCountry, onDismiss }: FirstRoundCoachProps) {
  const [acknowledged, setAcknowledged] = useState(false);
  const hoverPointer = useHoverPointer();

  const step = coachStep(acknowledged, hasGuess);
  const { order, title, text } = texts(hoverPointer, byCountry)[step];

  return (
    <aside className={styles.coach} aria-live="polite">
      <p className={styles.counter}>
        Шаг {order} из {ORDER.length}
      </p>
      <h2 className={styles.title}>{title}</h2>
      <p className={styles.text}>{text}</p>

      <div className={styles.actions}>
        {step === "look" && (
          <Button
            variant="primary"
            size="small"
            onClick={() => {
              setAcknowledged(true);
            }}
          >
            Понятно
          </Button>
        )}

        <button type="button" className={styles.skip} onClick={onDismiss}>
          Не показывать
        </button>
      </div>
    </aside>
  );
}
