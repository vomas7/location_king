/**
 * Комната на двоих: хост создаёт, второй игрок входит по коду и попадает в
 * общую таблицу.
 */

import { expect, test } from "@playwright/test";

import { open, playRounds, register } from "./helpers";

test("двое играют одну серию и сравнивают результаты", async ({ browser, page }) => {
  const host = await register(page);

  // Условия комнаты берутся из одиночной партии
  await page.getByRole("radio", { name: "3", exact: true }).first().click();

  await open(page, "Комната");
  await page.getByRole("button", { name: "Создать комнату" }).click();

  // Код комнаты — единственный шестизначный абзац на экране
  const shown = page
    .locator("p")
    .filter({ hasText: /^[A-Z2-9]{6}$/ })
    .first();
  await expect(shown).toBeVisible();

  const code = await shown.textContent();
  expect(code).not.toBeNull();

  await expect(page.getByText("Пока никто не вошёл. Отправь ссылку друзьям.")).toBeVisible();

  // Второй игрок — своя вкладка со своим входом
  const guestContext = await browser.newContext();
  const guestPage = await guestContext.newPage();
  const guest = await register(guestPage);

  await open(guestPage, "Комната");
  await guestPage.getByLabel("Код комнаты").fill(code!);
  await guestPage.getByRole("button", { name: "Войти" }).click();

  await expect(guestPage.getByText(code!)).toBeVisible();
  await expect(guestPage.getByText(/хост /)).toContainText(host.name);

  await guestPage.getByRole("button", { name: "Играть", exact: true }).click();
  await expect(guestPage.getByRole("progressbar")).toHaveAttribute("aria-valuemax", "3");

  await playRounds(guestPage, 3);
  await guestPage.getByRole("button", { name: "В меню" }).click();

  // Таблица комнаты у хоста обновляется сама
  await expect(page.getByText(guest.name)).toBeVisible({ timeout: 20_000 });

  await guestContext.close();
});

test("в закрытую комнату войти нельзя", async ({ browser, page }) => {
  await register(page);

  await open(page, "Комната");
  await page.getByRole("button", { name: "Создать комнату" }).click();

  // Код комнаты — единственный шестизначный абзац на экране
  const shown = page
    .locator("p")
    .filter({ hasText: /^[A-Z2-9]{6}$/ })
    .first();
  await expect(shown).toBeVisible();

  const code = await shown.textContent();
  expect(code).not.toBeNull();

  await page.getByRole("button", { name: "Закрыть набор" }).click();
  await expect(page.getByText(/набор закрыт/)).toBeVisible();

  const guestContext = await browser.newContext();
  const guestPage = await guestContext.newPage();
  await register(guestPage);

  await guestPage.goto(`/?room=${code!}`);

  await expect(guestPage.getByText("Набор закрыт — войти уже нельзя.")).toBeVisible();
  await expect(guestPage.getByRole("button", { name: "Играть", exact: true })).toHaveCount(0);

  await guestContext.close();
});
