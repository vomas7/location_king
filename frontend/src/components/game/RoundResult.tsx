/** Результат раунда: где была цель и сколько это стоило. */

import { useEffect, useRef } from "react";

import type { RoundResult as RoundResultData } from "~/api/types";
import styles from "~/components/game/RoundResult.module.css";
import { Button } from "~/components/ui/Button";
import { useFocusTrap } from "~/components/ui/useFocusTrap";
import { formatDistance, formatNumber, formatPercent } from "~/domain/format";
import { scoreRatio, scoreTier } from "~/domain/score";
import { COLOR_GUESS, COLOR_TARGET } from "~/map/styles";
import { createResultMap, type ResultMap } from "~/map/result";

const TIER_CLASS: Record<string, string | undefined> = {
  perfect: styles.tierPerfect,
  great: styles.tierGreat,
  good: styles.tierGood,
  fair: styles.tierFair,
  poor: styles.tierPoor,
};

interface RoundResultProps {
  result: RoundResultData;
  isLastRound: boolean;
  onNext: () => void;
}

export function RoundResult({ result, isLastRound, onNext }: RoundResultProps) {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<ResultMap | null>(null);
  const nextButton = useRef<HTMLButtonElement>(null);
  const dialog = useRef<HTMLDivElement>(null);

  useFocusTrap(dialog);

  useEffect(() => {
    const element = container.current;
    if (element === null) return;

    const map = createResultMap(element);
    instance.current = map;

    return () => {
      map.destroy();
      instance.current = null;
    };
  }, []);

  useEffect(() => {
    instance.current?.show(result.target, result.guess);
    nextButton.current?.focus();
  }, [result]);

  const tier = scoreTier(result.score, result.max_score);
  const ratio = scoreRatio(result.score, result.max_score);

  const place = [result.zone.country, result.zone.region, result.zone.difficulty_name]
    .filter((value): value is string => value !== null && value !== "")
    .join(" · ");

  return (
    <div
      ref={dialog}
      className={styles.overlay}
      role="dialog"
      aria-modal="true"
      aria-label="Результат раунда"
    >
      <div className={styles.sheet}>
        <div className={styles.map} ref={container} />

        <div className={styles.panel}>
          <p className={[styles.tier, TIER_CLASS[tier.tone]].filter(Boolean).join(" ")}>
            {tier.label}
          </p>

          <div aria-live="polite">
            <h2 className={styles.score}>
              {formatNumber(result.score)}
              <small>из {formatNumber(result.max_score)} очков</small>
            </h2>
          </div>

          <div className={styles.bar}>
            <div
              className={[styles.barFill, TIER_CLASS[tier.tone]].filter(Boolean).join(" ")}
              style={{ width: `${String(ratio * 100)}%` }}
            />
          </div>

          <div className={styles.readouts}>
            <div className={styles.readout}>
              <span className={styles.readoutLabel}>Промах</span>
              <span className={styles.readoutValue}>{formatDistance(result.distance_km)}</span>
            </div>
            <div className={styles.readout}>
              <span className={styles.readoutLabel}>Точность</span>
              <span className={styles.readoutValue}>{formatPercent(result.accuracy)}</span>
            </div>
          </div>

          <div className={styles.place}>
            <p className={styles.placeName}>{result.zone.name}</p>
            {place !== "" && <p className={styles.placeMeta}>{place}</p>}

            <div className={styles.legend}>
              <span className={styles.legendItem}>
                <span className={styles.dot} style={{ background: COLOR_TARGET }} />
                цель
              </span>
              <span className={styles.legendItem}>
                <span className={styles.dot} style={{ background: COLOR_GUESS }} />
                твоя точка
              </span>
            </div>
          </div>

          <Button ref={nextButton} variant="primary" size="large" block onClick={onNext}>
            {isLastRound ? "Посмотреть итоги" : "Следующий раунд"}
          </Button>
        </div>
      </div>
    </div>
  );
}
