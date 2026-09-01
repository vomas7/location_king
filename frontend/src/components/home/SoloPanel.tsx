/**
 * Одиночная партия.
 *
 * Условия лежат открыто, все сразу. Раньше они были свёрнуты в строку под
 * кнопкой «Настроить» — считалось, что чаще всего игрок начинает партию на тех
 * же условиях, что и прошлую. На деле вышло иначе: игроки не знали, что
 * условия вообще есть, и год играли одним режимом на одном уровне.
 *
 * Так что порядок здесь линейный: игрок выбрал, с кем играет, — и сразу видит,
 * во что именно. Ничего не спрятано, а тому, кому всё равно, по-прежнему
 * достаточно нажать «Начать игру»: всё уже выставлено.
 */

import styles from "~/components/home/SoloPanel.module.css";
import { Alert } from "~/components/ui/Alert";
import { Button } from "~/components/ui/Button";
import { CardSubtitle, CardTitle } from "~/components/ui/Card";
import { Segmented } from "~/components/ui/Segmented";
import type { GameSetup } from "~/domain/setup";
import {
  ANSWER_MODES,
  answerModeHint,
  LEVELS,
  levelHint,
  PLACES,
  ROUNDS,
  TIME_LIMITS,
} from "~/domain/setup";

interface SoloPanelProps {
  setup: GameSetup;
  onChange: (change: Partial<GameSetup>) => void;
  /** Сколько зон подходит под выбранные уровень и место. null — неизвестно. */
  zoneCount: number | null;
  error: string | null;
  /** Первая партия: настраивать ещё нечего, всё выставлено за игрока. */
  newcomer: boolean;
  onStart: () => void;
}

export function SoloPanel({
  setup,
  onChange,
  zoneCount,
  error,
  newcomer,
  onStart,
}: SoloPanelProps) {
  const empty = zoneCount === 0;
  // И карта стран, и выбор из шести спрашивают страну: место в условиях
  // партии в обоих случаях было бы готовым ответом
  const byCountry = setup.answerMode !== "point";

  return (
    <section>
      <CardTitle>Одиночная партия</CardTitle>
      <CardSubtitle>
        {newcomer
          ? "Для первой партии всё уже выставлено: пять раундов по городам, которые узнают все. Просто жми «Начать»"
          : "Раунд за раундом, только ты и снимок"}
      </CardSubtitle>

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

        <Segmented
          label="Сложность"
          options={LEVELS}
          value={setup.level}
          onChange={(level) => {
            onChange({ level });
          }}
          hint={levelHint(setup.level)}
        />

        {/* В режиме стран выбирать место нельзя: «Россия» в условиях
            партии — это и есть ответ на все её раунды */}
        {byCountry ? (
          <p className={styles.note}>
            В режиме стран играем по всему миру: выбранное место подсказывало бы ответ.
          </p>
        ) : (
          <Segmented
            label="Где играем"
            options={PLACES}
            value={setup.place}
            onChange={(place) => {
              onChange({ place });
            }}
            {...(zoneCount === null ? {} : { hint: `Подходящих зон: ${String(zoneCount)}` })}
          />
        )}

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

      {empty && (
        <p className={styles.warning}>
          На таких условиях зон нет. Возьми другой уровень или другое место.
        </p>
      )}

      {error !== null && (
        <div className={styles.alertSlot}>
          <Alert message={error} />
        </div>
      )}

      <Button variant="primary" size="large" block disabled={empty} onClick={onStart}>
        Начать игру
      </Button>
    </section>
  );
}
