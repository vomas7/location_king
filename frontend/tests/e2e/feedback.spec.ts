/**
 * Обратная связь.
 *
 * Проверяется путь целиком: игрок нашёл форму в меню, написал и получил
 * подтверждение. Что написанное доехало до базы, проверяет бэкенд.
 */

import { expect, test } from "@playwright/test";

import { open, register } from "./helpers";

test("игрок пишет о проблеме прямо из меню", async ({ page }) => {
  await register(page);

  await open(page, "Профиль");
  await page.getByRole("button", { name: "Отзыв об игре" }).click();

  const dialog = page.getByRole("dialog", { name: "Отзыв об игре" });
  await expect(dialog).toBeVisible();

  // По умолчанию впечатление: о поломке говорят реже, чем об игре
  await dialog.getByRole("radio", { name: "Проблема" }).click();
  await dialog.getByLabel("Сообщение").fill("Карта догадки не открывается на планшете");
  await dialog.getByRole("button", { name: "Отправить" }).click();

  await expect(dialog.getByText("Дошло, спасибо")).toBeVisible();

  await dialog.getByRole("button", { name: "Закрыть" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("пустой отзыв не отправляется", async ({ page }) => {
  await register(page);

  await open(page, "Профиль");
  await page.getByRole("button", { name: "Отзыв об игре" }).click();

  const dialog = page.getByRole("dialog", { name: "Отзыв об игре" });
  await dialog.getByLabel("Сообщение").fill("   ");
  await dialog.getByRole("button", { name: "Отправить" }).click();

  await expect(dialog.getByRole("alert")).toContainText("Напиши, что случилось");
  await expect(dialog.getByText("Дошло, спасибо")).toHaveCount(0);
});
