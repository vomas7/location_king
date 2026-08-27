/** Стили точек и линий на картах. */

import Circle from "ol/style/Circle";
import Fill from "ol/style/Fill";
import RegularShape from "ol/style/RegularShape";
import Stroke from "ol/style/Stroke";
import Style from "ol/style/Style";

/**
 * Значение токена из tokens.css.
 *
 * OpenLayers принимает только готовые строки цвета, var() он не понимает.
 * Дублировать значения в двух местах нельзя, поэтому читаем их из стилей.
 * Запасной цвет нужен на случай, если модуль исполнится до применения CSS.
 */
function token(name: string, fallback: string): string {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value === "" ? fallback : value;
}

/** Цвет точки игрока. Тот же, что у акцента интерфейса. */
export const COLOR_GUESS = token("--accent", "#38bdf8");

/** Цвет цели. Тот же, что у очков. */
export const COLOR_TARGET = token("--gold", "#fbbf24");

const OUTLINE = token("--bg", "#080b11");

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
