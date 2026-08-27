/** Карта мира, на которой игрок ставит точку. */

import type { Map as OlMap } from "ol";
import MapBrowser from "ol/Map";
import View from "ol/View";
import Feature from "ol/Feature";
import Point from "ol/geom/Point";
import TileLayer from "ol/layer/Tile";
import VectorLayer from "ol/layer/Vector";
import OSM from "ol/source/OSM";
import VectorSource from "ol/source/Vector";
import { defaults as defaultControls } from "ol/control/defaults";
import { fromLonLat, toLonLat } from "ol/proj";

import { STYLE_GUESS } from "~/map/styles";

/** Точка на глобусе. */
export interface LonLat {
  longitude: number;
  latitude: number;
}

export interface GuessMap {
  readonly map: OlMap;
  clear: () => void;
  /** Пересчитать размеры после того, как контейнер изменился. */
  refresh: () => void;
  destroy: () => void;
}

export function baseLayer(): TileLayer<OSM> {
  return new TileLayer({ source: new OSM({ attributions: "© OpenStreetMap" }) });
}

export function createGuessMap(target: HTMLElement, onPick: (point: LonLat) => void): GuessMap {
  const source = new VectorSource();

  const map = new MapBrowser({
    target,
    layers: [baseLayer(), new VectorLayer({ source, style: STYLE_GUESS })],
    controls: defaultControls({ attribution: false, rotate: false }),
    view: new View({
      center: fromLonLat([20, 30]),
      zoom: 1,
      minZoom: 1,
      maxZoom: 18,
    }),
  });

  map.on("click", (event) => {
    const [longitude, latitude] = toLonLat(event.coordinate);
    if (longitude === undefined || latitude === undefined) return;

    source.clear();
    source.addFeature(new Feature(new Point(event.coordinate)));
    onPick({ longitude, latitude });
  });

  return {
    map,
    clear: () => {
      source.clear();
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
