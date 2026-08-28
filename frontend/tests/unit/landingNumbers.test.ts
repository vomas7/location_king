/**
 * Числа на посадочной странице против настоящего каталога.
 *
 * «Мест в игре» — обещание, которое легко дать и невозможно заметить, когда
 * оно устарело: каталог живёт в бэкенде, страница — во фронтенде, и связи
 * между ними нет никакой. Пока её нет, число проверяется здесь.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

// От каталога frontend, откуда запускается vitest
const SEED = resolve(process.cwd(), "../backend/scripts/seed.py");
const LANDING = resolve(process.cwd(), "src/components/landing/LandingScreen.tsx");

/** Сколько ZoneSpec в каталоге. */
function zonesInCatalog(): number {
  return readFileSync(SEED, "utf8").split("ZoneSpec(").length - 1;
}

/** Число под подписью «Мест в игре» на странице. */
function zonesOnLanding(): number {
  const html = readFileSync(LANDING, "utf8");
  const found = /<dt>Мест в игре<\/dt>[\s\S]*?<dd>(\d+)<\/dd>/.exec(html);

  expect(found, "на странице нет блока «Мест в игре»").not.toBeNull();
  return Number(found?.[1]);
}

describe("числа на посадочной странице", () => {
  it("каталог не пустой", () => {
    expect(zonesInCatalog()).toBeGreaterThan(50);
  });

  it("«Мест в игре» совпадает с каталогом", () => {
    expect(zonesOnLanding()).toBe(zonesInCatalog());
  });
});
