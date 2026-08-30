/**
 * Режим выбора: шесть названий вместо карты.
 *
 * Самый простой вход в игру — и он должен быть виден из меню сразу, а не
 * из-под кнопки «Настроить».
 */

import { expect, test } from "@playwright/test";

import { register } from "./helpers";

test("режимы видны в меню, не разворачивая настройки", async ({ page }) => {
  await register(page);

  // Все три способа ответа на виду: до этого «Страной» лежало под
  // «Настроить», и игрок мог не узнать, что режим вообще есть
  for (const mode of ["Из шести", "Страной", "Точкой"]) {
    await expect(page.getByRole("radio", { name: mode })).toBeVisible();
  }
});

test("игрок отвечает выбором из шести стран", async ({ page }) => {
  await register(page);

  await page.getByRole("radio", { name: "Из шести" }).click();
  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  const options = page.getByRole("radiogroup", { name: "Из какой страны снимок" });
  await expect(options.getByRole("radio")).toHaveCount(6);

  // Карты догадки в этом режиме нет вовсе: отвечают названием
  await expect(page.getByRole("button", { name: "Открыть карту" })).toHaveCount(0);

  // Пока страна не выбрана, отвечать нечем
  const answer = page.getByRole("button", { name: "Ответить" });
  await expect(answer).toBeDisabled();

  await options.getByRole("radio").first().click();
  await expect(answer).toBeEnabled();
  await answer.click();

  const result = page.getByRole("dialog");
  await expect(result.getByText("Твой ответ")).toBeVisible();
  await expect(result.getByText("Страна", { exact: true })).toBeVisible();
});

test("в простом режиме подсказку не продают", async ({ page }) => {
  await register(page);

  await page.getByRole("radio", { name: "Из шести" }).click();
  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  // «Это в Африке» вычёркивает половину списка разом: упрощать самый простой
  // режим ещё раз, да ещё за очки, незачем
  await expect(page.getByRole("button", { name: /Подсказка/ })).toHaveCount(0);
});
