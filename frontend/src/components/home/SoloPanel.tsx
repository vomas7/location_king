/**
 * Одиночная партия.
 *
 * Условия свёрнуты в одну строку, а не разложены пятью переключателями:
 * чаще всего игрок начинает партию на тех же условиях, что и прошлую, и
 * пролистывать ради этого экран настроек ему незачем. Строка при этом
 * называет условия целиком — свёрнутое не значит спрятанное.
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
  describeSetup,
  EXTENTS,
  LEVELS,
  levelHint,
  PLACES,
  ROUNDS,
  TIME_LIMITS,
} from "~/domain/setup";

interface SoloPanelProps {
  setup: GameSetup;
  /** Развёрнуты ли настройки. Состояние снаружи: в них приходят из комнаты. */
  open: boolean;
  onToggle: () => void;
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
  open,
  onToggle,
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

      <div className={styles.setup}>
        <p className={styles.summary}>{describeSetup(setup)}</p>
        <button
          type="button"
          className={styles.toggle}
          aria-expanded={open}
          aria-controls="solo-setup"
          onClick={onToggle}
        >
          {open ? "Свернуть" : "Настроить"}
        </button>
      </div>

      {/* Чем отвечать — главный выбор в игре, а не строка настроек. Пока он
          лежал под кнопкой «Настроить», игрок мог год играть точками и не
          узнать, что есть режимы попроще */}
      <div className={styles.mode}>
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
      </div>

      {open && (
        <div id="solo-setup" className={styles.options}>
          <Segmented
            label="Раундов"
            options={ROUNDS}
            value={setup.rounds}
            onChange={(rounds) => {
              onChange({ rounds });
            }}
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
          <Segmented
            label="Размер участка"
            options={EXTENTS}
            value={setup.extent}
            onChange={(extent) => {
              onChange({ extent });
            }}
            hint="Чем меньше участок, тем труднее узнать место"
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
          <Segmented
            label="Время на раунд"
            options={TIME_LIMITS}
            value={setup.timeLimit}
            onChange={(timeLimit) => {
              onChange({ timeLimit });
            }}
            hint="Чем быстрее ответ, тем больше очков за раунд"
          />
        </div>
      )}

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
