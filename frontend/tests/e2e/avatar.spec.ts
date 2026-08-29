/**
 * Своя аватарка.
 *
 * Проверяется путь целиком: игрок нашёл загрузку в профиле, выбрал файл и
 * увидел картинку вместо узора. Что сервер оставляет от файла одни пиксели,
 * проверяет бэкенд.
 */

import { expect, test } from "@playwright/test";

import { open, register } from "./helpers";

/** Прямоугольная картинка: сервер обязан обрезать её в квадрат. */
const PICTURE = "tests/e2e/fixtures-avatar.png";

test("игрок ставит свою аватарку и возвращает узор", async ({ page }) => {
  await register(page);

  await open(page, "Профиль");
  await page.getByRole("button", { name: "Изменить" }).click();

  // До загрузки аватарка рисуется узором, то есть это svg, а не картинка
  await expect(page.locator("#section-panel img[alt*='Аватарка']")).toHaveCount(0);

  await page.setInputFiles('input[type="file"]', PICTURE);

  await expect(page.getByText("Своя картинка")).toBeVisible();
  const picture = page.locator("#section-panel img[alt*='Аватарка']").first();
  await expect(picture).toBeVisible();

  // Квадрат: обрезал сервер, клиент растянуть прямоугольник не мог
  const box = await picture.boundingBox();
  expect(box).not.toBeNull();
  expect(Math.abs((box?.width ?? 0) - (box?.height ?? 0))).toBeLessThan(2);

  await page.getByRole("button", { name: "Убрать" }).click();

  await expect(page.getByText("Своя картинка")).toBeHidden();
  await expect(page.locator("#section-panel img[alt*='Аватарка']")).toHaveCount(0);
});

test("аватарка остаётся после перезахода", async ({ page }) => {
  await register(page);

  await open(page, "Профиль");
  await page.getByRole("button", { name: "Изменить" }).click();
  await page.setInputFiles('input[type="file"]', PICTURE);
  await expect(page.getByText("Своя картинка")).toBeVisible();

  await page.reload();
  await open(page, "Профиль");

  await expect(page.locator("#section-panel img[alt*='Аватарка']").first()).toBeVisible();
});

test("не картинку сервер не берёт", async ({ page }) => {
  await register(page);

  await open(page, "Профиль");
  await page.getByRole("button", { name: "Изменить" }).click();

  await page.setInputFiles('input[type="file"]', {
    name: "me.png",
    mimeType: "image/png",
    buffer: Buffer.from("совсем не картинка"),
  });

  await expect(page.getByRole("alert")).toContainText(/картинка|повреждён/i);
});
