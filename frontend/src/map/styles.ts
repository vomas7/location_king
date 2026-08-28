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

/**
 * Цель — тёплая, ответ игрока — холодный.
 *
 * Это не украшение, а кодировка: на карте результата две точки, и по цвету
 * должно быть сразу понятно, где правда, а где догадка. Цель совпадает с
 * акцентом интерфейса, потому что именно к ней всё время ведут очки.
 */
export const COLOR_TARGET = token("--accent", "#ffab2e");
export const COLOR_GUESS = token("--marker-guess", "#56c7f0");

const OUTLINE = token("--bg", "#070d0c");

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

/** Линия промаха между догадкой и целью. */
export const STYLE_LINE = new Style({
  stroke: new Stroke({ color: token("--text-dim", "#9fb3ad"), width: 2, lineDash: [6, 6] }),
});

/**
 * Перекрестие в центре показанного участка.
 *
 * Очки считаются от этой точки, поэтому игрок должен видеть, куда целиться, —
 * на снегу, на тёмной воде, на пёстрой застройке и на любой яркости экрана.
 * Отсюда три слоя: широкая тёмная подложка, белые линии поверх неё и янтарное
 * кольцо тем же цветом, каким цель отмечена на карте результата. Один белый
 * штрих в два пикселя, как было раньше, на светлом снимке попросту теряется.
 */
const RETICLE_RADIUS = 22;

export const STYLE_CENTER: Style[] = [
  new Style({
    image: new RegularShape({
      points: 4,
      radius: RETICLE_RADIUS,
      radius2: 0,
      stroke: new Stroke({ color: "rgba(0, 0, 0, 0.65)", width: 8 }),
    }),
  }),
  new Style({
    image: new RegularShape({
      points: 4,
      radius: RETICLE_RADIUS,
      radius2: 0,
      stroke: new Stroke({ color: "rgba(255, 255, 255, 0.98)", width: 3 }),
    }),
  }),
  // Кольцо вокруг самой точки: тёмный контур снаружи, янтарь внутри. Центр
  // остаётся открытым — под ним должно быть видно, что именно ищем
  new Style({
    image: new Circle({
      radius: 8,
      stroke: new Stroke({ color: "rgba(0, 0, 0, 0.65)", width: 6 }),
    }),
  }),
  new Style({
    image: new Circle({
      radius: 8,
      stroke: new Stroke({ color: COLOR_TARGET, width: 3 }),
    }),
  }),
];
