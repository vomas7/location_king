/**
 * Общая часть меню перед партией.
 *
 * Условия лежат открыто, все сразу. Раньше они были свёрнуты в строку под
 * кнопкой «Настроить» — считалось, что чаще всего игрок начинает партию на тех
 * же условиях, что и прошлую. На деле вышло иначе: игроки не знали, что
 * условия вообще есть, и играли одним режимом на одном уровне.
 *
 * Что спрашивают все режимы, спрашивается здесь: чем отвечать, сколько раундов
 * и на время ли. Своё каждый режим доносит потомками — у одиночной это уровень
 * и место, у известных мест своего нет вовсе.
 */

import type { ReactNode } from "react";

import styles from "~/components/home/SetupPanel.module.css";
import { Alert } from "~/components/ui/Alert";
import { Button } from "~/components/ui/Button";
import { CardSubtitle, CardTitle } from "~/components/ui/Card";
import { Segmented } from "~/components/ui/Segmented";
import type { GameSetup } from "~/domain/setup";
import { ANSWER_MODES, answerModeHint, ROUNDS, TIME_LIMITS } from "~/domain/setup";

interface SetupPanelProps {
  title: string;
  subtitle: ReactNode;
  setup: GameSetup;
  onChange: (change: Partial<GameSetup>) => void;
  /** Условия этого режима: встают между выбором ответа и длиной партии. */
  children?: ReactNode;
  /** Почему играть на таких условиях нельзя. Пусто — можно. */
  warning?: string | null;
  error: string | null;
  onStart: () => void;
}

export function SetupPanel({
  title,
  subtitle,
  setup,
  onChange,
  children,
  warning = null,
  error,
  onStart,
}: SetupPanelProps) {
  return (
    <section>
      <CardTitle>{title}</CardTitle>
      <CardSubtitle>{subtitle}</CardSubtitle>

      <div className={styles.options}>
        {/* Чем отвечать — главный выбор в игре, поэтому он первый: от него
            зависит, во что игрок будет играть, а не насколько трудно */}
        <Segmented
          label="Чем отвечать"
          options={ANSWER_MODES}
          value={setup.answerMode}
          onChange={(answerMode) => {
            // Выбор места вместе с ответом страной — это уже не игра:
            // «Россия» в условиях партии и есть правильный ответ
            onChange({ answerMode, ...(answerMode === "point" ? {} : { place: null }) });
          }}
          hint={answerModeHint(setup.answerMode)}
        />

        {children}

        {/* Сколько играем и как долго — про форму партии, а не про её
            содержание, поэтому стоят парой и на широком экране делят строку */}
        <div className={styles.pair}>
          <Segmented
            label="Раундов"
            options={ROUNDS}
            value={setup.rounds}
            onChange={(rounds) => {
              onChange({ rounds });
            }}
          />

          <Segmented
            label="Время на раунд"
            options={TIME_LIMITS}
            value={setup.timeLimit}
            onChange={(timeLimit) => {
              onChange({ timeLimit });
            }}
            hint="Чем быстрее ответ, тем больше очков"
          />
        </div>
      </div>

      {warning !== null && <p className={styles.warning}>{warning}</p>}

      {error !== null && (
        <div className={styles.alertSlot}>
          <Alert message={error} />
        </div>
      )}

      <Button variant="primary" size="large" block disabled={warning !== null} onClick={onStart}>
        Начать игру
      </Button>
    </section>
  );
}
