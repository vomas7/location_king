/** Стили точек и линий на картах. */

import Circle from "ol/style/Circle";
import Fill from "ol/style/Fill";
import RegularShape from "ol/style/RegularShape";
import Stroke from "ol/style/Stroke";
import Style from "ol/style/Style";

export const COLOR_GUESS = "#38bdf8";
export const COLOR_TARGET = "#fbbf24";

const OUTLINE = "#080b11";

function marker(color: string): Style {
  return new Style({
    image: new Circle({
      radius: 8,
      fill: new Fill({ color }),
      stroke: new Stroke({ color: OUTLINE, width: 3 }),
    }),
  });
}

export const STYLE_GUESS = marker(COLOR_GUESS);
export const STYLE_TARGET = marker(COLOR_TARGET);

export const STYLE_LINE = new Style({
  stroke: new Stroke({ color: "#e2e8f0", width: 2, lineDash: [6, 6] }),
});

/**
 * Перекрестие в центре показанного участка.
 *
 * Очки считаются от этой точки, поэтому игрок должен видеть, куда целиться.
 * Тёмная подложка нужна, чтобы метка читалась и на снегу, и на тёмной воде.
 */
export const STYLE_CENTER: Style[] = [
  new Style({
    image: new RegularShape({
      points: 4,
      radius: 16,
      radius2: 0,
      stroke: new Stroke({ color: "rgba(0, 0, 0, 0.55)", width: 5 }),
    }),
  }),
  new Style({
    image: new RegularShape({
      points: 4,
      radius: 16,
      radius2: 0,
      stroke: new Stroke({ color: "rgba(255, 255, 255, 0.95)", width: 2 }),
    }),
  }),
  new Style({
    image: new Circle({
      radius: 5,
      stroke: new Stroke({ color: "rgba(255, 255, 255, 0.95)", width: 2 }),
    }),
  }),
];
