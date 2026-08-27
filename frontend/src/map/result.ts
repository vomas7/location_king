/** Карта результата: цель, догадка и линия между ними. */

import type { Map as OlMap } from "ol";
import MapBrowser from "ol/Map";
import View from "ol/View";
import Feature from "ol/Feature";
import LineString from "ol/geom/LineString";
import Point from "ol/geom/Point";
import VectorLayer from "ol/layer/Vector";
import VectorSource from "ol/source/Vector";
import { defaults as defaultInteractions } from "ol/interaction/defaults";
import { fromLonLat } from "ol/proj";

import { osmControls, osmLayer } from "~/map/osm";
import { STYLE_GUESS, STYLE_LINE, STYLE_TARGET } from "~/map/styles";

type Coordinates = [number, number];

export interface ResultMap {
  readonly map: OlMap;
  show: (target: Coordinates, guess: Coordinates | null) => void;
  destroy: () => void;
}

export function createResultMap(target: HTMLElement): ResultMap {
  const source = new VectorSource();

  const map = new MapBrowser({
    target,
    layers: [
      osmLayer(),
      new VectorLayer({
        source,
        style: (feature) => {
          const kind = feature.get("kind") as string;
          if (kind === "line") return STYLE_LINE;
          return kind === "target" ? STYLE_TARGET : STYLE_GUESS;
        },
      }),
    ],
    controls: osmControls(),
    interactions: defaultInteractions({ mouseWheelZoom: false }),
    view: new View({ center: [0, 0], zoom: 1 }),
  });

  return {
    map,

    show(targetPoint, guessPoint) {
      source.clear();

      const targetFeature = new Feature(new Point(fromLonLat(targetPoint)));
      targetFeature.set("kind", "target");
      source.addFeature(targetFeature);

      if (guessPoint !== null) {
        const guessFeature = new Feature(new Point(fromLonLat(guessPoint)));
        guessFeature.set("kind", "guess");

        const line = new Feature(new LineString([fromLonLat(guessPoint), fromLonLat(targetPoint)]));
        line.set("kind", "line");

        source.addFeatures([guessFeature, line]);
      }

      const extent = source.getExtent();
      if (extent === null) return;

      map.updateSize();
      map.getView().fit(extent, {
        size: map.getSize(),
        padding: [60, 60, 60, 60],
        maxZoom: 12,
        duration: 400,
      });
    },

    destroy: () => {
      map.setTarget(undefined);
      map.dispose();
    },
  };
}
