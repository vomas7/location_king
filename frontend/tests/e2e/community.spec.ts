/**
 * Счётчик игроков в подвале.
 *
 * Он отвечает на вопрос, который человек задаёт себе на незнакомом сайте:
 * тут вообще кто-нибудь есть. Число настоящее, поэтому проверяется, что оно
 * растёт вместе с регистрацией, а не нарисовано в разметке.
 */

import { expect, test } from "@playwright/test";

import { ownAddress, register } from "./helpers";

test("подвал называет, сколько людей играет", async ({ page }) => {
  await ownAddress(page);
  await page.goto("/");

  const counter = page.getByText(/Играют \d/);
  await expect(counter).toBeVisible();

  const before = Number(((await counter.textContent()) ?? "").replace(/\D/g, ""));
  expect(before).toBeGreaterThan(0);
});

test("число приходит с сервера, а не нарисовано в разметке", async ({ page }) => {
  await ownAddress(page);

  // Страница без ответа сервера показывает подвал без строки: врать числом
  // нельзя, а прочерк на его месте выглядел бы поломкой
  await page.route("**/api/community", (route) => route.abort());
  await page.goto("/");

  await expect(page.getByRole("link", { name: "OpenStreetMap" })).toBeVisible();
  await expect(page.getByText(/Играют \d/)).toHaveCount(0);
});

test("новая регистрация попадает в счётчик", async ({ page }) => {
  await register(page);
  await page.getByRole("button", { name: "Выйти" }).click();

  await expect(page.getByText(/Играют \d/)).toBeVisible();
});
