/** Посадочная страница: содержание, переходы и форма входа на месте. */

import { expect, test } from "@playwright/test";

test("рассказывает про игру и ведёт к регистрации", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { level: 1 })).toContainText("Найди точку");
  await expect(page.getByRole("heading", { name: "Как проходит раунд" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Во что играть" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Частые вопросы" })).toBeVisible();

  // Ссылка «как это работает» доводит до раздела с шагами
  await page.getByRole("link", { name: "Как это работает" }).click();
  await expect(page.getByText("Смотришь на снимок")).toBeInViewport();

  // Главная кнопка возвращает к форме входа
  await page.getByRole("link", { name: "Играть бесплатно" }).click();
  await expect(page.getByRole("tab", { name: "Регистрация" })).toBeInViewport();

  // В подвале — ссылка на исходники: игра открыта, и это видно со страницы
  await expect(page.getByRole("link", { name: "Исходный код" })).toHaveAttribute(
    "href",
    /github\.com\/[^/]+\/location_king/,
  );
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
