/**
 * Подсказка раунда: одна плашка поверх снимка.
 *
 * Живёт не в панели догадки, а рядом со снимком, потому что решение платить
 * за неё очками игрок принимает, глядя на снимок: на телефоне панель почти
 * весь раунд свёрнута в кнопку, и подсказка, спрятанная внутрь неё, стоила бы
 * лишнего нажатия.
 *
 * Взятая подсказка занимает то же место, что и кнопка: это одно и то же —
 * до нажатия цена, после нажатия ответ.
 */

import type { RoundView } from "~/api/types";
import styles from "~/components/game/GameScreen.module.css";
import { useFormats, useText } from "~/state/languageContext";

interface HintControlProps {
  round: RoundView;
  busy: boolean;
  /** Взять подсказку: чем именно платит игрок, знает сервер. */
  onHint: () => void;
}

export function HintControl({ round, busy, onHint }: HintControlProps) {
  const formats = useFormats();
  const { game: text } = useText();
  if (round.hint !== null) {
    return (
      <p className={`${styles.glass} ${styles.revealed}`}>
        <span>{round.hint.label}</span>
        <strong>{round.hint.value}</strong>
      </p>
    );
  }

  // Нулевая цена означает, что раскрывать нечего: предлагать нечего тоже
  if (round.hint_cost === 0) return null;

  return (
    <button
      type="button"
      className={`${styles.glass} ${styles.hintButton}`}
      disabled={busy}
      onClick={onHint}
    >
      {text.hint}
      <span>{text.hintCost(formats.number(round.hint_cost))}</span>
    </button>
  );
}
