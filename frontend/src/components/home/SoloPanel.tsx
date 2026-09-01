/**
 * Одиночная партия.
 *
 * Кроме общих условий здесь спрашивают уровень и место: это единственный
 * режим, который играет по всему каталогу, и разделить его на посильные части
 * больше нечем.
 */

import { SetupPanel } from "~/components/home/SetupPanel";
import styles from "~/components/home/SetupPanel.module.css";
import { Segmented } from "~/components/ui/Segmented";
import type { GameSetup } from "~/domain/setup";
import { LEVELS, levelHint, PLACES } from "~/domain/setup";

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
  // И карта стран, и выбор из шести спрашивают страну: место в условиях
  // партии в обоих случаях было бы готовым ответом
  const byCountry = setup.answerMode !== "point";

  return (
    <SetupPanel
      title="Одиночная партия"
      subtitle={
        newcomer
          ? "Для первой партии всё уже выставлено: пять раундов по городам, которые узнают все. Просто жми «Начать»"
          : "Раунд за раундом, только ты и снимок"
      }
      setup={setup}
      onChange={onChange}
      warning={
        zoneCount === 0
          ? "На таких условиях зон нет. Возьми другой уровень или другое место."
          : null
      }
      error={error}
      onStart={onStart}
    >
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
    </SetupPanel>
  );
}
