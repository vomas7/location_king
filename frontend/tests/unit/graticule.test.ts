/**
 * Координатная сетка первого экрана.
 *
 * Смысл сетки в том, что её линии — настоящие меридианы и параллели, а
 * подпись под прицелом с ними сходится. Проверяется именно это: арифметика
 * проекции и то, как координаты читаются вслух.
 */

import { describe, expect, it } from "vitest";

import {
  formatCoordinates,
  LAT_LIMIT,
  latitudeAt,
  longitudeAt,
  MERIDIANS,
  meridianOffset,
  mercatorY,
  PARALLELS,
  parallelOffset,
} from "~/domain/graticule";

describe("проекция", () => {
  it("экватор лежит посередине", () => {
    expect(mercatorY(0)).toBeCloseTo(0, 12);
    expect(parallelOffset(0)).toBeCloseTo(0.5, 10);
    expect(latitudeAt(0.5)).toBeCloseTo(0, 10);
  });

  it("край сетки — это её предельная широта", () => {
    expect(parallelOffset(LAT_LIMIT)).toBeCloseTo(0, 10);
    expect(latitudeAt(0)).toBeCloseTo(LAT_LIMIT, 10);
    expect(latitudeAt(1)).toBeCloseTo(-LAT_LIMIT, 10);
  });

  it("широта растёт кверху, долгота вправо", () => {
    expect(latitudeAt(0.2)).toBeGreaterThan(latitudeAt(0.8));
    expect(longitudeAt(0.8)).toBeGreaterThan(longitudeAt(0.2));
  });

  it("долгота идёт от края до края", () => {
    expect(longitudeAt(0)).toBe(-180);
    expect(longitudeAt(1)).toBe(180);
    expect(meridianOffset(0)).toBeCloseTo(0.5, 10);
  });

  it("за краями ничего не считается: там сетки нет", () => {
    expect(longitudeAt(-1)).toBe(-180);
    expect(latitudeAt(2)).toBeCloseTo(-LAT_LIMIT, 10);
  });

  /**
   * Ровно то, ради чего сетка нарисована в Меркаторе: к полюсам параллели
   * расходятся. На равномерной решётке шестидесятая и тридцатая стояли бы
   * на одинаковом расстоянии от экватора и от края.
   */
  it("параллели расходятся к полюсу, а не стоят через равные промежутки", () => {
    const toThirty = parallelOffset(0) - parallelOffset(30);
    const thirtyToSixty = parallelOffset(30) - parallelOffset(60);

    expect(thirtyToSixty).toBeGreaterThan(toThirty);
  });

  it("подпись сходится с линией: на широте параллели читается её градус", () => {
    for (const latitude of PARALLELS) {
      expect(latitudeAt(parallelOffset(latitude))).toBeCloseTo(latitude, 8);
    }

    for (const longitude of MERIDIANS) {
      expect(longitudeAt(meridianOffset(longitude))).toBeCloseTo(longitude, 8);
    }
  });
});

describe("запись координат", () => {
  it("одни числа: полушарие показывает знак", () => {
    expect(formatCoordinates(55.7558, 37.6173)).toBe("55.76, 37.62");
    expect(formatCoordinates(-33.8688, -70.6693)).toBe("-33.87, -70.67");
  });

  /** Ровно на экваторе и нулевом меридиане, куда прицел попадает запросто. */
  it("не пишет минус ноль: он читается как ошибка вычисления", () => {
    expect(formatCoordinates(-0.001, -0.002)).toBe("0.00, 0.00");
    expect(formatCoordinates(0, 0)).toBe("0.00, 0.00");
  });
});
