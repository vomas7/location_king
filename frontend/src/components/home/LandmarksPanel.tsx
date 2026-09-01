/**
 * Известные места.
 *
 * Отдельный слой каталога: не города, а объекты, которые узнают сами по себе —
 * Колизей, Тадж-Махал, Пальма Джумейра. Показываются крупным планом, и в этом
 * весь смысл: Колизей в кадре на сорок пять километров — это Рим, а не
 * Колизей.
 *
 * Условий здесь меньше, чем в одиночной, и это не упрощение ради вида. Уровень
 * и место у такого набора не спрашивают: объектов пара десятков, они разбросаны
 * по всем частям света, и пересечение с «хардкором» или «Океанией» оставило бы
 * игрока без единой зоны. Остаётся то, что действительно выбирают: чем
 * отвечать, сколько раундов и на время ли.
 */

import styles from "~/components/home/SoloPanel.module.css";
import { Alert } from "~/components/ui/Alert";
import { Button } from "~/components/ui/Button";
import { CardSubtitle, CardTitle } from "~/components/ui/Card";
import { Segmented } from "~/components/ui/Segmented";
import type { GameSetup } from "~/domain/setup";
import { ANSWER_MODES, answerModeHint, ROUNDS, TIME_LIMITS } from "~/domain/setup";

interface LandmarksPanelProps {
  setup: GameSetup;
  onChange: (change: Partial<GameSetup>) => void;
  error: string | null;
  onStart: () => void;
}

export function LandmarksPanel({ setup, onChange, error, onStart }: LandmarksPanelProps) {
  return (
    <section>
      <CardTitle>Известные места</CardTitle>
      <CardSubtitle>
        Пирамиды Гизы, Колизей, Тадж-Махал, Пальма Джумейра — крупным планом, без города вокруг
      </CardSubtitle>

      <div className={styles.options}>
        <Segmented
          label="Чем отвечать"
          options={ANSWER_MODES}
          value={setup.answerMode}
          onChange={(answerMode) => {
            onChange({ answerMode });
          }}
          hint={answerModeHint(setup.answerMode)}
        />

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

      {error !== null && (
        <div className={styles.alertSlot}>
          <Alert message={error} />
        </div>
      )}

      <Button variant="primary" size="large" block onClick={onStart}>
        Начать игру
      </Button>
    </section>
  );
}
