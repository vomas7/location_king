/** Правовая часть: документы, уведомление о хранилище и удаление аккаунта. */

import { expect, test } from "@playwright/test";

import { register } from "./helpers";

test("документы открываются из подвала и на экране входа", async ({ page }) => {
  await page.goto("/");

  // Уведомление о хранилище встречает нового игрока
  const notice = page.getByRole("note", { name: "О хранилище браузера" });
  await expect(notice).toBeVisible();

  await notice.getByRole("button", { name: "Подробнее" }).click();

  const dialog = page.getByRole("dialog", { name: "Куки и хранилище браузера" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("Куки мы не ставим")).toBeVisible();

  await dialog.getByRole("tab", { name: "Конфиденциальность" }).click();
  await expect(page.getByRole("dialog", { name: "Политика конфиденциальности" })).toBeVisible();

  await page.getByRole("button", { name: "Закрыть" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);

  // Закрытое уведомление не возвращается после перезагрузки
  await notice.getByRole("button", { name: "Понятно" }).click();
  await page.reload();
  await expect(page.getByRole("note", { name: "О хранилище браузера" })).toHaveCount(0);
});

test("без согласия с условиями аккаунт не создать", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: "Регистрация" }).click();
  await page.getByPlaceholder("you@example.com").fill("no-consent@example.com");
  await page.getByPlaceholder(/Не короче/).fill("long enough password");

  await page.getByRole("button", { name: "Создать аккаунт" }).click();

  await expect(page.getByRole("alert")).toContainText("принять условия");
  await expect(page.getByRole("button", { name: "Начать игру" })).toHaveCount(0);
});

test("подпись об источнике карты видна игроку", async ({ page }) => {
  await register(page);
  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  await page.locator(".ol-viewport").nth(1).hover();
  await expect(page.getByRole("link", { name: "OpenStreetMap" }).first()).toBeVisible();
});

test("аккаунт удаляется вместе с данными", async ({ page }) => {
  const player = await register(page);

  await page.getByRole("button", { name: "Удалить аккаунт" }).click();

  const dialog = page.getByRole("dialog", { name: "Удаление учётной записи" });
  await expect(dialog).toBeVisible();

  // Чужой пароль не подходит
  await dialog.getByPlaceholder("Подтверди, что это ты").fill("совсем другой пароль");
  await dialog.getByRole("button", { name: "Удалить навсегда" }).click();
  await expect(page.getByRole("alert")).toContainText("Неверный пароль");

  await dialog.getByPlaceholder("Подтверди, что это ты").fill(player.password);
  await dialog.getByRole("button", { name: "Удалить навсегда" }).click();

  // Выбросило на экран входа, и войти прежней парой уже нельзя
  await expect(page.getByRole("tab", { name: "Регистрация" })).toBeVisible();

  await page.getByPlaceholder("you@example.com").fill(player.email);
  await page.getByPlaceholder(/Не короче/).fill(player.password);
  await page.getByRole("button", { name: "Войти" }).click();

  await expect(page.getByRole("alert")).toContainText("Неверный email или пароль");
});
