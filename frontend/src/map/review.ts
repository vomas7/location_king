/**
 * Карта разбора партии: все раунды сразу.
 *
 * Отдельно от карты одного раунда: там нужно показать один промах крупно, а
 * здесь — увидеть партию целиком и понять, где именно её проиграли. Раунды
 * пронумерованы теми же номерами, что и строки списка под картой.
 */

import type { Map as OlMap } from "ol";
import Feature from "ol/Feature";
import type { FeatureLike } from "ol/Feature";
import MapBrowser from "ol/Map";
import View from "ol/View";
import LineString from "ol/geom/LineString";
import Point from "ol/geom/Point";
import { defaults as defaultInteractions } from "ol/interaction/defaults";
import VectorLayer from "ol/layer/Vector";
import { fromLonLat } from "ol/proj";
import VectorSource from "ol/source/Vector";

import { osmControls, osmLayer } from "~/map/osm";
import type Style from "ol/style/Style";

import { STYLE_GUESS, STYLE_LINE, styleNumberedTarget } from "~/map/styles";

type Coordinates = [number, number];

/** Раунд глазами карты: где была цель и куда ткнул игрок. */
export interface ReviewRound {
  index: number;
  target: Coordinates;
  /** Пусто у раунда, закрытого по времени: точку так и не поставили. */
  guess: Coordinates | null;
}

export interface ReviewMap {
  readonly map: OlMap;
  /** Показать партию. Выбранный раунд подсвечен, остальные приглушены. */
  show: (rounds: ReviewRound[], selected: number | null) => void;
  destroy: () => void;
}

/** Насколько гасятся раунды, кроме выбранного. */
const DIMMED = 0.35;

function roundFeatures(round: ReviewRound): Feature[] {
  const target = new Feature(new Point(fromLonLat(round.target)));
  target.set("index", round.index);

  if (round.guess === null) return [target];

  const guess = new Feature(new Point(fromLonLat(round.guess)));
  guess.set("kind", "guess");

  const line = new Feature(new LineString([fromLonLat(round.guess), fromLonLat(round.target)]));
  line.set("kind", "line");

  // Цель рисуется последней: номер раунда должен лежать поверх линии
  return [line, guess, target];
}

function styleOf(feature: FeatureLike): Style {
  const kind = feature.get("kind") as string | undefined;
  if (kind === "line") return STYLE_LINE;
  if (kind === "guess") return STYLE_GUESS;
  return styleNumberedTarget(feature.get("index") as number);
}

export function createReviewMap(target: HTMLElement, credit: string): ReviewMap {
  // Два слоя вместо прозрачных цветов: приглушить целый слой — это одно
  // свойство, а не пересборка каждого стиля с альфа-каналом
  const dimmed = new VectorSource();
  const active = new VectorSource();

  const map = new MapBrowser({
    target,
    layers: [
      osmLayer(credit),
      new VectorLayer({ source: dimmed, opacity: DIMMED, style: styleOf }),
      new VectorLayer({ source: active, style: styleOf }),
    ],
    controls: osmControls(),
    interactions: defaultInteractions({ mouseWheelZoom: false }),
    view: new View({ center: [0, 0], zoom: 1 }),
  });

  return {
    map,

    show(rounds, selected) {
      dimmed.clear();
      active.clear();

      for (const round of rounds) {
        const target = selected === null || round.index === selected ? active : dimmed;
        target.addFeatures(roundFeatures(round));
      }

      // Приближаемся к тому, что подсвечено: без выбора это вся партия, с
      // выбором — один раунд. Пустой источник отдаёт бесконечный охват, по
      // которому карта улетела бы в никуда
      const extent = active.getExtent();
      if (extent === null || !extent.every(Number.isFinite)) return;

      map.updateSize();
      map.getView().fit(extent, {
        size: map.getSize(),
        padding: [48, 48, 48, 48],
        maxZoom: 9,
        duration: 400,
      });
    },

    destroy: () => {
      map.setTarget(undefined);
      map.dispose();
    },
  };
}
