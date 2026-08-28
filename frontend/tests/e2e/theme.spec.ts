/**
 * Оформление интерфейса.
 *
 * Главное здесь — не палитра, а то, что выбор хранится у игрока: он должен
 * пережить и перезагрузку страницы, и чистое хранилище на новом устройстве.
 */

import { expect, test } from "@playwright/test";

import { register } from "./helpers";

test("выбранная тема остаётся после перезахода", async ({ page }) => {
  const player = await register(page);

  await page.getByRole("radio", { name: "Светлая" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");

  // Новое устройство — это чистое хранилище и тот же аккаунт
  await page.getByRole("button", { name: "Выйти" }).click();
  await page.evaluate(() => {
    localStorage.clear();
  });
  await page.reload();

  await page.getByPlaceholder("you@example.com").fill(player.email);
  await page.getByPlaceholder(/Не короче/).fill(player.password);
  await page.getByRole("button", { name: "Войти" }).click();

  await expect(page.getByRole("button", { name: "Начать игру" })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("«как в системе» слушает настройку браузера", async ({ page }) => {
  await register(page);

  await page.getByRole("radio", { name: "Как в системе" }).click();

  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");

  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});
