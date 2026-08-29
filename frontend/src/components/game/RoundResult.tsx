/** Результат раунда: где была цель и сколько это стоило. */

import { useEffect, useRef } from "react";

import type { RoundResult as RoundResultData } from "~/api/types";
import styles from "~/components/game/RoundResult.module.css";
import { Button } from "~/components/ui/Button";
import { useModal } from "~/components/ui/useModal";
import { formatDistance, formatNumber, formatPercent } from "~/domain/format";
import { scoreRatio, scoreTier, zoneStanding } from "~/domain/score";
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

  useModal(dialog, true);

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

  // Режим стран отличаем по заполненной стране цели: в обычном раунде
  // вопрос был не про страну, и сервер её не считает
  const byCountry = result.country !== null;

  // Промах в километрах сам по себе ничего не говорит: 340 км — это много
  // или мало? Ответ даёт то, как ту же зону отыграли остальные. В режиме
  // стран километров на экране нет вовсе: очки дали не за них
  const standing = zoneStanding(
    result.distance_km === null ? null : Number.parseFloat(result.distance_km),
    result.zone.total_rounds,
    result.zone.average_distance,
  );

  const place = [result.zone.country, result.zone.region]
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

          {/* В режиме стран вопрос был не про километры, и отвечать на него
              промахом значило бы объяснять очки не тем, за что их дали */}
          <div className={styles.readouts}>
            {byCountry ? (
              <>
                <div className={styles.readout}>
                  <span className={styles.readoutLabel}>Страна</span>
                  <span className={styles.readoutName}>{result.country}</span>
                </div>
                <div className={styles.readout}>
                  <span className={styles.readoutLabel}>Твой ответ</span>
                  <span className={styles.readoutName}>{result.guess_country ?? "мимо суши"}</span>
                </div>
              </>
            ) : (
              <>
                <div className={styles.readout}>
                  <span className={styles.readoutLabel}>Промах</span>
                  <span className={styles.readoutValue}>{formatDistance(result.distance_km)}</span>
                </div>
                <div className={styles.readout}>
                  <span className={styles.readoutLabel}>Точность</span>
                  <span className={styles.readoutValue}>{formatPercent(result.accuracy)}</span>
                </div>
              </>
            )}
          </div>

          <div className={styles.place}>
            <p className={styles.placeName}>{result.zone.name}</p>
            {place !== "" && <p className={styles.placeMeta}>{place}</p>}

            {!byCountry && standing !== null && (
              <p className={styles.standing}>
                Здесь обычно промахиваются на {formatDistance(standing.averageKm)} —{" "}
                <span className={standing.better ? styles.betterThanOthers : undefined}>
                  {standing.better ? "ты точнее" : "ты дальше"}
                </span>
              </p>
            )}

            <div className={styles.legend}>
              <span className={styles.legendItem}>
                <span className={styles.dot} style={{ background: COLOR_TARGET }} />
                цель
              </span>
              {/* В раунде про страны точки нет вовсе: игрок называл страну */}
              {result.guess !== null && (
                <span className={styles.legendItem}>
                  <span className={styles.dot} style={{ background: COLOR_GUESS }} />
                  твоя точка
                </span>
              )}
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
