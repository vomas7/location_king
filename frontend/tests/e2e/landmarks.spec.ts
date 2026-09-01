/**
 * Известные места — отдельный слой каталога.
 *
 * Проверяется то, ради чего он и сделан: объект показывают крупным планом,
 * а в обычную партию он не попадает.
 */

import type { Page } from "@playwright/test";
import { expect, test } from "@playwright/test";

import { answerRound, open, register } from "./helpers";

/** Сколько километров обещает бейдж масштаба на снимке. */
async function frameKm(page: Page): Promise<number> {
  const badge = await page.getByText(/участок ~/).textContent();
  const found = /~\s*([\d.]+)/.exec(badge ?? "");
  expect(found).not.toBeNull();

  return Number(found![1]);
}

test("известные места видны в меню и показываются крупным планом", async ({ page }) => {
  await register(page);

  await open(page, "Известные места");
  await expect(page.getByText(/Пирамиды Гизы, Колизей/)).toBeVisible();

  // Уровень и место здесь не спрашивают: объектов пара десятков на весь мир
  await expect(page.getByRole("radiogroup", { name: "Сложность" })).toHaveCount(0);
  await expect(page.getByRole("radiogroup", { name: "Где играем" })).toHaveCount(0);

  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  expect(await frameKm(page)).toBeLessThan(25);
});

test("обычная партия крупных планов не выдаёт", async ({ page }) => {
  await register(page);

  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  expect(await frameKm(page)).toBeGreaterThan(25);
});

test("в известных местах играют и отвечают", async ({ page }) => {
  await register(page);

  await open(page, "Известные места");
  await page.getByRole("radio", { name: "3", exact: true }).first().click();
  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  await page.getByRole("button", { name: "Не показывать" }).click();
  await answerRound(page);

  // Раунд закрылся и объект назван: это и есть суть режима
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("из 5 000 очков")).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Следующий раунд" })).toBeVisible();
});
