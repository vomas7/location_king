/**
 * Игра с телефона.
 *
 * Главное отличие от десктопа: наведения курсора не существует, поэтому карта
 * догадки должна открываться нажатием. Заодно проверяем, что ничего не
 * вылезает за край экрана.
 */

import { expect, test, type Page } from "@playwright/test";

import { register } from "./helpers";

test.use({
  viewport: { width: 390, height: 844 },
  hasTouch: true,
  isMobile: true,
});

/** Ширина содержимого не должна превышать ширину экрана. */
async function expectNoSideScroll(page: Page) {
  const overflow = await page.evaluate(
    () => document.body.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, "содержимое вылезает за край экрана").toBeLessThanOrEqual(1);
}

test("посадочная страница помещается в экран телефона", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expectNoSideScroll(page);

  await page.getByRole("link", { name: "Играть бесплатно" }).click();
  await expect(page.getByRole("tab", { name: "Регистрация" })).toBeInViewport();
});

test("раунд играется пальцем: карта открывается нажатием", async ({ page }) => {
  await register(page);
  await expectNoSideScroll(page);

  await page.getByRole("radio", { name: "3", exact: true }).first().click();
  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  // Ничего не вылезло за край даже с шапкой и панелью
  await expectNoSideScroll(page);

  // Наведения нет, поэтому карта закрыта и открывается кнопкой
  await expect(page.getByRole("button", { name: "Ответить" })).toHaveCount(0);
  await page.getByRole("button", { name: "Открыть карту" }).click();

  const guessMap = page.locator(".ol-viewport").nth(1);
  await expect(guessMap).toBeVisible();

  const box = await guessMap.boundingBox();
  expect(box).not.toBeNull();
  await page.mouse.click(box!.x + box!.width * 0.5, box!.y + box!.height * 0.5);

  await page.getByRole("button", { name: "Ответить" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();

  // Результат на узком экране складывается в одну колонку и помещается
  await expect(page.getByRole("button", { name: "Следующий раунд" })).toBeInViewport();
});
