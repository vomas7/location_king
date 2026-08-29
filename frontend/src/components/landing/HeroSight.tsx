/**
 * Прицел на первом экране.
 *
 * Сзади — координатная сетка, по ней ходит перекрестие и называет широту и
 * долготу точки, на которую наведено. Это ровно то, чем игрок занимается в
 * партии, только показанное до входа: ткнуть в место на планете.
 *
 * Числа настоящие. Меридианы и параллели стоят там, где им положено в
 * проекции Меркатора, — той самой, в которой в игре показана карта мира, —
 * и подпись под перекрестием с ними сходится. Сетка, у которой линии
 * ничего не значат, была бы просто решёткой на фоне.
 *
 * Мышью прицел ведут курсором, пальцем — касанием: наведения на телефоне не
 * существует, а без второго пути перекрестие там навсегда осталось бы там,
 * где его поставили при загрузке.
 */

import { useEffect, useRef, type RefObject } from "react";

import styles from "~/components/landing/HeroSight.module.css";
import {
  formatCoordinates,
  latitudeAt,
  longitudeAt,
  MERIDIANS,
  meridianOffset,
  PARALLELS,
  parallelOffset,
} from "~/domain/graticule";

/** Где стоит перекрестие, пока его никуда не навели. */
const START = { x: 0.3, y: 0.7 };

/** Зазор между подписью и краем экрана. */
const MARGIN = 18;

interface HeroSightProps {
  /** Первый экран: по нему водят прицелом и от него считают координаты. */
  hero: RefObject<HTMLElement>;
}

export function HeroSight({ hero }: HeroSightProps) {
  const cross = useRef<HTMLDivElement>(null);
  const readout = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    const area = hero.current;
    const crossNode = cross.current;
    const readoutNode = readout.current;
    if (area === null || crossNode === null || readoutNode === null) return;

    // Доли, а не пиксели: от них считаются и координаты, и положение, и
    // после смены размера окна ничего не съезжает
    let ratio = START;
    let frame = 0;

    // Перекрестие ходит за курсором, а перерисовка React на каждое движение
    // мыши — это десятки кадров в секунду впустую. Поэтому положение
    // пишется прямо в стиль узла, а кадр запрашивается один
    const draw = () => {
      frame = 0;

      const box = area.getBoundingClientRect();
      const x = ratio.x * box.width;
      const y = ratio.y * box.height;

      crossNode.style.transform = `translate(${String(x)}px, ${String(y)}px)`;
      readoutNode.textContent = formatCoordinates(latitudeAt(ratio.y), longitudeAt(ratio.x));

      // Подпись перекидываем на левую сторону по её настоящей ширине, а не по
      // доле экрана: на телефоне она занимает половину строки, и любой
      // заранее выбранный порог там врал бы
      const width = readoutNode.offsetWidth;
      const fits = x + MARGIN + width + MARGIN <= box.width;
      const left = fits ? x + MARGIN : x - MARGIN - width;

      readoutNode.style.transform = `translate(${String(left)}px, ${String(y + MARGIN)}px)`;
    };

    const schedule = () => {
      if (frame === 0) frame = window.requestAnimationFrame(draw);
    };

    const aim = (event: PointerEvent) => {
      const box = area.getBoundingClientRect();
      if (box.width === 0 || box.height === 0) return;

      ratio = {
        x: (event.clientX - box.left) / box.width,
        y: (event.clientY - box.top) / box.height,
      };
      schedule();
    };

    area.addEventListener("pointermove", aim, { passive: true });
    area.addEventListener("pointerdown", aim, { passive: true });
    window.addEventListener("resize", schedule, { passive: true });

    schedule();

    return () => {
      area.removeEventListener("pointermove", aim);
      area.removeEventListener("pointerdown", aim);
      window.removeEventListener("resize", schedule);
      if (frame !== 0) window.cancelAnimationFrame(frame);
    };
  }, [hero]);

  return (
    <div className={styles.sight} aria-hidden="true">
      <Graticule />

      <div ref={cross} className={styles.cross}>
        <span className={styles.horizontal} />
        <span className={styles.vertical} />
        <span className={styles.ring} />
      </div>

      {/* Подпись отдельно от перекрестия: у неё своё смещение от него, и
          на узком экране она перекидывается на другую сторону */}
      <p ref={readout} className={styles.readout} />
    </div>
  );
}

/**
 * Сетка. Растягивается по экрану без сохранения пропорций — она фон, а не
 * карта, — поэтому толщину линий держим независимой от растяжения.
 */
function Graticule() {
  return (
    <svg className={styles.grid} viewBox="0 0 1000 1000" preserveAspectRatio="none">
      <g vectorEffect="non-scaling-stroke">
        {MERIDIANS.map((longitude) => {
          const x = meridianOffset(longitude) * 1000;
          // На телефоне меридианы через тридцать градусов встают чаще, чем
          // раз в тридцать пикселей: там остаются только шестидесятые
          return (
            <line
              key={`m${String(longitude)}`}
              className={longitude % 60 === 0 ? styles.line : styles.minor}
              x1={x}
              y1="0"
              x2={x}
              y2="1000"
              vectorEffect="non-scaling-stroke"
            />
          );
        })}

        {PARALLELS.map((latitude) => {
          const y = parallelOffset(latitude) * 1000;
          return (
            <line
              key={`p${String(latitude)}`}
              className={latitude === 0 ? styles.equator : styles.line}
              x1="0"
              y1={y}
              x2="1000"
              y2={y}
              vectorEffect="non-scaling-stroke"
            />
          );
        })}
      </g>
    </svg>
  );
}
