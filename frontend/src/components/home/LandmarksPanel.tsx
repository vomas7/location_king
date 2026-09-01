/**
 * Известные места.
 *
 * Отдельный слой каталога: не города, а объекты, которые узнают сами по себе —
 * Колизей, Тадж-Махал, Пальма Джумейра. Показываются крупным планом, и в этом
 * весь смысл: Колизей в кадре на сорок пять километров — это Рим, а не
 * Колизей.
 *
 * Своих условий у режима нет, и это не упрощение ради вида. Уровень и место у
 * такого набора не спрашивают: объектов пара десятков, они разбросаны по всем
 * частям света, и пересечение с «хардкором» или «Океанией» оставило бы игрока
 * без единой зоны.
 */

import { SetupPanel } from "~/components/home/SetupPanel";
import type { GameSetup } from "~/domain/setup";
import { useText } from "~/state/languageContext";

interface LandmarksPanelProps {
  setup: GameSetup;
  onChange: (change: Partial<GameSetup>) => void;
  error: string | null;
  onStart: () => void;
}

export function LandmarksPanel({ setup, onChange, error, onStart }: LandmarksPanelProps) {
  const text = useText();

  return (
    <SetupPanel
      title={text.setup.landmarksTitle}
      subtitle={text.setup.landmarksSubtitle}
      setup={setup}
      onChange={onChange}
      error={error}
      onStart={onStart}
    />
  );
}
