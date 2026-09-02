/** Посадочная страница: содержание, переходы и форма входа на месте. */

import { expect, test } from "@playwright/test";

test("рассказывает про игру и ведёт к регистрации", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { level: 1 })).toContainText("Земля сверху");
  await expect(page.getByRole("heading", { name: "Как проходит раунд" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Во что играть" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Частые вопросы" })).toBeVisible();

  // Ссылка «как это устроено» доводит до раздела с шагами
  await page.getByRole("link", { name: "Как это устроено" }).click();
  await expect(page.getByText("Смотришь на квадрат съёмки")).toBeInViewport();

  // Сыграть можно, ничего не заводя: это главное действие первого экрана
  await expect(page.getByRole("button", { name: /Сыграть пять раундов/ })).toBeVisible();

  // А к форме входа ведёт кнопка в самом низу страницы
  await page.getByRole("link", { name: "Начать игру" }).click();
  await expect(page.getByRole("tab", { name: "Регистрация" })).toBeInViewport();

  // В подвале — ссылка на исходники: игра открыта, и это видно со страницы
  await expect(page.getByRole("link", { name: "Исходный код" })).toHaveAttribute(
    "href",
    /github\.com\/[^/]+\/location_king/,
  );
});

test("прицел на первом экране называет настоящие координаты", async ({ page }) => {
  await page.goto("/");

  const readout = page.getByText(/^-?\d+\.\d\d, -?\d+\.\d\d$/);
  await expect(readout).toBeVisible();

  const hero = page.getByRole("heading", { level: 1 }).locator("xpath=ancestor::section[1]");
  const box = await hero.boundingBox();
  expect(box).not.toBeNull();

  const aim = async (x: number, y: number) => {
    await page.mouse.move(box!.x + box!.width * x, box!.y + box!.height * y);
  };

  // Координаты не украшение: справа от нулевого меридиана и выше экватора
  // оба числа положительные, слева и ниже — оба со знаком минус
  await aim(0.8, 0.3);
  await expect(readout).toHaveText(/^\d+\.\d\d, \d+\.\d\d$/);

  await aim(0.2, 0.85);
  await expect(readout).toHaveText(/^-\d+\.\d\d, -\d+\.\d\d$/);
});

test("страница описана для поисковика", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveTitle(/Location King/);

  const description = page.locator('meta[name="description"]');
  await expect(description).toHaveAttribute("content", /геогессер/i);

  await expect(page.locator('meta[property="og:image:width"]')).toHaveAttribute("content", "1200");
  await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute(
    "content",
    "summary_large_image",
  );
});

test("пароль можно посмотреть глазом", async ({ page }) => {
  await page.goto("/");

  const password = page.getByPlaceholder(/Не короче/);
  await password.fill("моё-секретное-слово");
  await expect(password).toHaveAttribute("type", "password");

  // Пароль набирают вслепую, и на телефоне это главный повод бросить
  // регистрацию: увидеть, где опечатка, нечем
  await page.getByRole("button", { name: "Показать пароль" }).click();
  await expect(password).toHaveAttribute("type", "text");

  await page.getByRole("button", { name: "Скрыть пароль" }).click();
  await expect(password).toHaveAttribute("type", "password");
});
