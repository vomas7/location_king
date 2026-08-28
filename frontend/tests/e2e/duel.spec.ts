/**
 * Дуэль: двое встают в очередь и получают общую серию раундов.
 *
 * Сценарий проверяет то, чего нет ни в одном другом: игроки находят друг
 * друга сами, без кода и без договорённости.
 */

import { expect, test } from "@playwright/test";

import { open, register } from "./helpers";

test("двое находят друг друга и играют дуэль", async ({ browser, page }) => {
  await register(page);

  // Счётчик виден на плитке режима, до того как игрок его открыл
  await expect(page.getByText("Сейчас никто не ищет")).toBeVisible();

  await open(page, "Дуэль");
  await page.getByRole("button", { name: "Найти соперника" }).click();
  await expect(page.getByText("Пока ищешь только ты")).toBeVisible();

  // Второй игрок — своя вкладка со своим входом
  const rivalContext = await browser.newContext();
  const rivalPage = await rivalContext.newPage();
  await register(rivalPage);

  await open(rivalPage, "Дуэль");
  await rivalPage.getByRole("button", { name: "Найти соперника" }).click();

  // Пара находится опросом, поэтому ждём дольше обычного
  await expect(rivalPage.getByRole("progressbar")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole("progressbar")).toBeVisible({ timeout: 20_000 });

  // Условия дуэли задаёт сервер: пять раундов и минута на раунд
  await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuemax", "5");

  await rivalContext.close();
});

test("рейтинг виден до первой дуэли", async ({ page }) => {
  await register(page);

  await open(page, "Дуэль");
  await expect(page.getByText("твой рейтинг", { exact: false })).toBeVisible();
  await expect(page.getByText("дуэлей ещё не было", { exact: false })).toBeVisible();
});

test("поиск можно отменить", async ({ page }) => {
  await register(page);

  await open(page, "Дуэль");
  await page.getByRole("button", { name: "Найти соперника" }).click();
  await expect(page.getByRole("button", { name: "Отменить поиск" })).toBeVisible();

  await page.getByRole("button", { name: "Отменить поиск" }).click();
  await expect(page.getByRole("button", { name: "Найти соперника" })).toBeVisible();
});
