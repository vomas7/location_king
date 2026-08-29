/**
 * Карта мира, на которой игрок отвечает.
 *
 * В обычном раунде он ставит точку, в раунде про страны — выбирает страну.
 * Это две разные механики на одной карте, поэтому режим задаётся при
 * создании и дальше не меняется: раунд не превращается из одного в другой.
 *
 * Контуры стран приезжают с сервера сильно упрощёнными. Точность им не нужна:
 * по ним только попадают пальцем, а сверяет ответ сервер по коду страны.
 */

import type { Map as OlMap } from "ol";
import type { FeatureLike } from "ol/Feature";
import MapBrowser from "ol/Map";
import View from "ol/View";
import Feature from "ol/Feature";
import GeoJSON from "ol/format/GeoJSON";
import Point from "ol/geom/Point";
import VectorLayer from "ol/layer/Vector";
import VectorSource from "ol/source/Vector";
import { fromLonLat, toLonLat } from "ol/proj";

import { countries } from "~/api/endpoints";
import type { Answer } from "~/api/types";
import { osmControls, osmLayer } from "~/map/osm";
import {
  STYLE_COUNTRY,
  STYLE_COUNTRY_HOVER,
  STYLE_COUNTRY_PICKED,
  STYLE_GUESS,
} from "~/map/styles";

export interface GuessMap {
  readonly map: OlMap;
  clear: () => void;
  /** Пересчитать размеры после того, как контейнер изменился. */
  refresh: () => void;
  destroy: () => void;
}

interface GuessMapOptions {
  /** Раунд про страны: вместо точки игрок выбирает страну. */
  byCountry: boolean;
  onPick: (answer: Answer) => void;
  /** Границы загружаются запросом, и до его конца выбирать нечего. */
  onCountriesReady?: (ready: boolean) => void;
}

export function createGuessMap(target: HTMLElement, options: GuessMapOptions): GuessMap {
  const marks = new VectorSource();
  const borders = new VectorSource();

  // Выбранная и подсвеченная страна живут здесь, а не в состоянии React:
  // стиль спрашивают на каждую перерисовку карты, и лишний рендер на каждое
  // движение мыши превратил бы наведение в слайд-шоу
  let picked: string | null = null;
  let hovered: string | null = null;

  const countryStyle = (feature: FeatureLike) => {
    const code = feature.get("code") as string;

    if (code === picked) return STYLE_COUNTRY_PICKED;
    if (code === hovered) return STYLE_COUNTRY_HOVER;
    return STYLE_COUNTRY;
  };

  const bordersLayer = new VectorLayer({ source: borders, style: countryStyle });

  const map = new MapBrowser({
    target,
    layers: options.byCountry
      ? [osmLayer(), bordersLayer]
      : [osmLayer(), new VectorLayer({ source: marks, style: STYLE_GUESS })],
    controls: osmControls(),
    view: new View({
      center: fromLonLat([20, 30]),
      zoom: 1,
      minZoom: 1,
      maxZoom: 18,
    }),
  });

  const countryAt = (pixel: number[]): Feature | null =>
    (map.forEachFeatureAtPixel(pixel, (feature) => feature) as Feature | undefined) ?? null;

  if (options.byCountry) {
    void (async () => {
      try {
        const collection = await countries.borders();
        borders.addFeatures(
          new GeoJSON().readFeatures(collection, { featureProjection: "EPSG:3857" }),
        );
        options.onCountriesReady?.(true);
      } catch {
        // Без границ выбрать страну нечем: панель скажет об этом сама
        options.onCountriesReady?.(false);
      }
    })();

    map.on("pointermove", (event) => {
      if (event.dragging) return;

      const feature = countryAt(event.pixel);
      const code = feature === null ? null : (feature.get("code") as string);

      if (code !== hovered) {
        hovered = code;
        bordersLayer.changed();
      }

      map.getTargetElement().style.cursor = code === null ? "" : "pointer";
    });

    map.on("click", (event) => {
      const feature = countryAt(event.pixel);
      if (feature === null) return;

      picked = feature.get("code") as string;
      bordersLayer.changed();

      options.onPick({
        kind: "country",
        code: picked,
        name: feature.get("name") as string,
      });
    });
  } else {
    map.on("click", (event) => {
      const [longitude, latitude] = toLonLat(event.coordinate);
      if (longitude === undefined || latitude === undefined) return;

      marks.clear();
      marks.addFeature(new Feature(new Point(event.coordinate)));
      options.onPick({ kind: "point", longitude, latitude });
    });
  }

  return {
    map,
    clear: () => {
      marks.clear();
      picked = null;
      hovered = null;
      bordersLayer.changed();
    },
    refresh: () => {
      map.updateSize();
    },
    destroy: () => {
      map.setTarget(undefined);
      map.dispose();
    },
  };
}
