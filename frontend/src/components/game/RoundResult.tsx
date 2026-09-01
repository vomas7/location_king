/** Результат раунда: где была цель и сколько это стоило. */

import { useEffect, useRef } from "react";

import type { RoundResult as RoundResultData } from "~/api/types";
import styles from "~/components/game/RoundResult.module.css";
import { Button } from "~/components/ui/Button";
import { useModal } from "~/components/ui/useModal";
import { scoreRatio, scoreTier, zoneStanding } from "~/domain/score";
import { COLOR_GUESS, COLOR_TARGET } from "~/map/styles";
import { createResultMap, type ResultMap } from "~/map/result";
import { useFormats, useText } from "~/state/languageContext";

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
  const formats = useFormats();
  const { game: text } = useText();
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<ResultMap | null>(null);
  const nextButton = useRef<HTMLButtonElement>(null);
  const dialog = useRef<HTMLDivElement>(null);

  useModal(dialog, true);

  useEffect(() => {
    const element = container.current;
    if (element === null) return;

    const map = createResultMap(element, text.mapCredit);
    instance.current = map;

    return () => {
      map.destroy();
      instance.current = null;
    };
  }, [text.mapCredit]);

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
      aria-label={text.resultLabel}
    >
      <div className={styles.sheet}>
        <div className={styles.map} ref={container} />

        <div className={styles.panel}>
          <p className={[styles.tier, TIER_CLASS[tier.tone]].filter(Boolean).join(" ")}>
            {text.tiers[tier.name]}
          </p>

          <div aria-live="polite">
            <h2 className={styles.score}>
              {formats.number(result.score)}
              <small>{text.outOf(formats.number(result.max_score))}</small>
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
                  <span className={styles.readoutLabel}>{text.country}</span>
                  <span className={styles.readoutName}>{result.country}</span>
                </div>
                <div className={styles.readout}>
                  <span className={styles.readoutLabel}>{text.yourAnswer}</span>
                  <span className={styles.readoutName}>
                    {result.guess_country ?? text.missedLand}
                  </span>
                </div>
              </>
            ) : (
              <>
                <div className={styles.readout}>
                  <span className={styles.readoutLabel}>{text.miss}</span>
                  <span className={styles.readoutValue}>
                    {formats.distance(result.distance_km)}
                  </span>
                </div>
                <div className={styles.readout}>
                  <span className={styles.readoutLabel}>{text.accuracy}</span>
                  <span className={styles.readoutValue}>{formats.percent(result.accuracy)}</span>
                </div>
              </>
            )}
          </div>

          <div className={styles.place}>
            <p className={styles.placeName}>{result.zone.name}</p>
            {place !== "" && <p className={styles.placeMeta}>{place}</p>}

            {!byCountry && standing !== null && (
              <p className={styles.standing}>
                {text.usualMiss(formats.distance(standing.averageKm))}
                <span className={standing.better ? styles.betterThanOthers : undefined}>
                  {standing.better ? text.youCloser : text.youFurther}
                </span>
              </p>
            )}

            <div className={styles.legend}>
              <span className={styles.legendItem}>
                <span className={styles.dot} style={{ background: COLOR_TARGET }} />
                {text.target}
              </span>
              {/* В раунде про страны точки нет вовсе: игрок называл страну */}
              {result.guess !== null && (
                <span className={styles.legendItem}>
                  <span className={styles.dot} style={{ background: COLOR_GUESS }} />
                  {text.yourPin}
                </span>
              )}
            </div>
          </div>

          <Button ref={nextButton} variant="primary" size="large" block onClick={onNext}>
            {isLastRound ? text.seeSummary : text.nextRound}
          </Button>
        </div>
      </div>
    </div>
  );
}
