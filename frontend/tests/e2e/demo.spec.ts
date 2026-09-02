/**
 * Знакомство с игрой без учётной записи.
 *
 * Проверяется главное обещание: с посадочной страницы можно сыграть, ничего
 * не заводя, и пройти все три способа отвечать — из списка, страной на карте
 * и точкой. В конце вместо продолжения игры зовут заводить учётную запись.
 */

import { expect, test, type Page } from "@playwright/test";

import { answerCountryRound, answerRound } from "./helpers";

/** Начать знакомство с посадочной страницы. */
async function startDemo(page: Page): Promise<void> {
  await page.goto("/");
  await page.getByRole("button", { name: /Сыграть пять раундов/ }).click();
  await expect(page.getByText("Место 1 из 5")).toBeVisible();
}

/** Ответить на раунд из списка стран. */
async function answerChoiceRound(page: Page): Promise<void> {
  await page.getByRole("radio").first().click();
  await page.getByRole("button", { name: "Ответить" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
}

/** Перейти к следующему раунду из окна результата. */
async function next(page: Page): Promise<void> {
  await page.getByRole("button", { name: /Следующий раунд|Посмотреть итоги/ }).click();
}

test("гость проходит знакомство и попадает на приглашение", async ({ page }) => {
  await startDemo(page);

  // Три раунда из списка: карты нет вовсе
  for (let round = 1; round <= 3; round += 1) {
    await expect(page.getByText(`Место ${String(round)} из 5`)).toBeVisible();
    await expect(page.getByText("Отвечаем из списка")).toBeVisible();
    await answerChoiceRound(page);
    await next(page);
  }

  // Четвёртый — карта стран: списка больше нет
  await expect(page.getByText("Место 4 из 5")).toBeVisible();
  await expect(page.getByText("Теперь по карте")).toBeVisible();
  await expect(page.getByRole("radio")).toHaveCount(0);
  await answerCountryRound(page);
  await next(page);

  // Пятый — настоящая игра: точка и километры
  await expect(page.getByText("Место 5 из 5")).toBeVisible();
  await expect(page.getByText("А это уже настоящая игра")).toBeVisible();
  await answerRound(page);
  await next(page);

  // В конце — не «сыграть ещё», а то, ради чего всё затевалось
  await expect(page.getByRole("heading", { name: "Пять мест позади" })).toBeVisible();
  await expect(page.getByText("297 мест вместо пяти")).toBeVisible();

  // Форма открывается сразу на регистрации: аккаунта у гостя заведомо нет
  await page.getByRole("button", { name: "Завести аккаунт" }).click();
  await expect(page.getByRole("tab", { name: "Регистрация" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
});

test("из знакомства можно выйти на полпути", async ({ page }) => {
  await startDemo(page);

  page.once("dialog", (dialog) => {
    void dialog.accept();
  });
  await page.getByRole("button", { name: "Выйти" }).click();

  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});

test("снимок знакомства отдаётся без единого токена", async ({ page }) => {
  // Токен в заголовке появляется только у авторизованного, и здесь его быть
  // не может: игрока ещё нет
  const authorized: string[] = [];
  page.on("request", (request) => {
    const header = request.headers()["authorization"];
    if (header !== undefined && request.url().includes("/api/demo/")) {
      authorized.push(request.url());
    }
  });

  await startDemo(page);
  await page.waitForTimeout(1500);

  const tiles = page.locator("canvas").first();
  await expect(tiles).toBeVisible();
  expect(authorized).toEqual([]);
});
