/**
 * Счётчик игроков в подвале.
 *
 * Он отвечает на вопрос, который человек задаёт себе на незнакомом сайте:
 * тут вообще кто-нибудь есть. Врать таким числом нельзя, поэтому проверяется
 * ровно это: строка показывает то, что ответил сервер, и исчезает, если он не
 * ответил. Само значение при этом не проверяется — на чистой базе ноль игроков
 * такой же правильный ответ, как и любой другой.
 */

import { expect, test } from "@playwright/test";

import { ownAddress } from "./helpers";

test("подвал называет, сколько людей играет", async ({ page }) => {
  await ownAddress(page);
  await page.goto("/");

  await expect(page.getByText(/Играют \d/)).toBeVisible();
});

test("показывается то число, которое назвал сервер", async ({ page }) => {
  await ownAddress(page);

  await page.route("**/api/community", (route) => route.fulfill({ json: { players: 42 } }));
  await page.goto("/");

  await expect(page.getByText("Играют 42 человека")).toBeVisible();
});

test("без ответа сервера строки просто нет", async ({ page }) => {
  await ownAddress(page);

  // Прочерк или ноль на месте настоящего числа выглядели бы поломкой, а
  // подвал от пропавшей строки не прыгает: строки в нём и так переносятся
  await page.route("**/api/community", (route) => route.abort());
  await page.goto("/");

  await expect(page.getByRole("link", { name: "OpenStreetMap" })).toBeVisible();
  await expect(page.getByText(/Играют \d/)).toHaveCount(0);
});
