/** Снимок раунда. Карта пересоздаётся на каждый раунд: у неё своя проекция. */

import { useEffect, useRef, useState } from "react";

import type { RoundView } from "~/api/types";
import styles from "~/components/game/GameScreen.module.css";
import { createSatelliteMap, type SatelliteMap } from "~/map/satellite";
import { formatExtent } from "~/domain/format";

interface SatelliteViewProps {
  round: RoundView;
  /** Счётчик, по изменению которого вид возвращается к исходному масштабу. */
  resetSignal: number;
}

export function SatelliteView({ round, resetSignal }: SatelliteViewProps) {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<SatelliteMap | null>(null);
  const [tilesMissing, setTilesMissing] = useState(false);

  useEffect(() => {
    const element = container.current;
    if (element === null) return;

    setTilesMissing(false);
    const map = createSatelliteMap(element, round, setTilesMissing);
    instance.current = map;

    return () => {
      map.destroy();
      instance.current = null;
    };
  }, [round]);

  useEffect(() => {
    if (resetSignal > 0) instance.current?.reset();
  }, [resetSignal]);

  return (
    <>
      <div className={styles.satellite} ref={container} />

      <div className={styles.badge}>
        <span className={styles.scale}>участок ~{formatExtent(round.view_extent_km)}</span>
        <span className={styles.credit}>{round.attribution}</span>
      </div>

      <div className={styles.hints} aria-hidden="true">
        <span>
          <kbd>M</kbd> карта · <kbd>Enter</kbd> ответить
        </span>
        <span>
          <kbd>R</kbd> вернуть масштаб · колесо — зум
        </span>
      </div>

      {tilesMissing && (
        <p className={styles.tileError} role="alert">
          Часть снимка не загрузилась. Подвигай карту — тайлы подгрузятся снова.
        </p>
      )}
    </>
  );
}
