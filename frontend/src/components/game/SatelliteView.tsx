/**
 * Снимок раунда. Карта пересоздаётся на каждый раунд: у неё своя проекция.
 *
 * Приборы поверх снимка — возврат к цели, подсказка, клавиши — собирает
 * экран игры одной колонкой: их порядок и отступы важны друг относительно
 * друга, а не относительно карты. Здесь остаётся только то, что описывает
 * сам снимок: масштаб и подпись источника.
 */

import { useEffect, useRef, useState } from "react";

import type { RoundView } from "~/api/types";
import styles from "~/components/game/GameScreen.module.css";
import { createSatelliteMap, type SatelliteMap } from "~/map/satellite";
import { useFormats } from "~/state/languageContext";

interface SatelliteViewProps {
  round: RoundView;
  /** Счётчик, по изменению которого вид возвращается к исходному масштабу. */
  resetSignal: number;
  /** Счётчик, по изменению которого север возвращается наверх. */
  northSignal: number;
  /** Снимок повёрнут: кнопку «На север» показывает экран игры. */
  onRotated: (rotated: boolean) => void;
}

export function SatelliteView({ round, resetSignal, northSignal, onRotated }: SatelliteViewProps) {
  const formats = useFormats();
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<SatelliteMap | null>(null);
  const [tilesMissing, setTilesMissing] = useState(false);

  // Карта пересоздаётся на каждый раунд, а обработчик поворота меняется на
  // каждый рендер: в зависимостях эффекта ему делать нечего
  const onRotatedRef = useRef(onRotated);
  onRotatedRef.current = onRotated;

  useEffect(() => {
    const element = container.current;
    if (element === null) return;

    setTilesMissing(false);
    // Новая карта всегда смотрит на север: экран игры об этом знает от нас, а
    // не догадывается по смене раунда
    onRotatedRef.current(false);

    const map = createSatelliteMap(element, round, {
      onMissingTiles: setTilesMissing,
      onRotated: (rotated) => {
        onRotatedRef.current(rotated);
      },
    });
    instance.current = map;

    return () => {
      map.destroy();
      instance.current = null;
    };
  }, [round]);

  useEffect(() => {
    if (resetSignal > 0) instance.current?.reset();
  }, [resetSignal]);

  useEffect(() => {
    if (northSignal > 0) instance.current?.straighten();
  }, [northSignal]);

  return (
    <>
      <div className={styles.satellite} ref={container} />

      <div className={`${styles.glass} ${styles.badge}`}>
        <span className={styles.scale}>участок ~{formats.extent(round.view_extent_km)}</span>
        <span className={styles.credit}>{round.attribution}</span>
      </div>

      {tilesMissing && (
        <p className={styles.tileError} role="alert">
          Часть снимка не загрузилась. Подвигай карту — тайлы подгрузятся снова.
        </p>
      )}
    </>
  );
}
