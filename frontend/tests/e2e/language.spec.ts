/**
 * Выбор языка.
 *
 * Русский — основной, но игру должно быть можно показать за пределами
 * русскоязычного интернета. Поэтому язык выбирается сам по языку браузера, а
 * переключить его можно из подвала — и выбор переживает перезагрузку.
 */

import { expect, test } from "@playwright/test";

import { register } from "./helpers";

test.describe("английский браузер", () => {
  test.use({ locale: "en-US" });

  test("сразу видит английскую страницу", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: /Find the place/ })).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
  });

  test("переключается на русский и помнит выбор", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Русский" }).click();

    await expect(page.getByRole("heading", { name: /Найди место/ })).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("lang", "ru");

    await page.reload();
    await expect(page.getByRole("heading", { name: /Найди место/ })).toBeVisible();
  });
});

test("русский браузер видит русскую страницу", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: /Найди место/ })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
});

test("на английском форма входа и подвал тоже английские", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "English" }).click();

  await expect(page.getByRole("tab", { name: "Sign up" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Source code" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Frequently asked" })).toBeVisible();
});

test("отказ сервера приходит на языке интерфейса", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "English" }).click();

  await page.getByPlaceholder("you@example.com").fill("nobody@example.com");
  await page.getByPlaceholder(/At least/).fill("whatever password");
  await page.getByRole("button", { name: "Log in" }).click();

  // Текст приходит с сервера: интерфейс его не придумывает, а только просит
  // отвечать по-английски
  await expect(page.getByText("Wrong email or password")).toBeVisible();
});

test("на английском место в результате раунда названо латиницей", async ({ page }) => {
  await register(page);
  await page.getByRole("button", { name: "English" }).click();

  await page.getByRole("button", { name: "Start playing" }).first().click();
  await expect(page.getByRole("button", { name: "Answer" })).toBeVisible();

  const coach = page.getByRole("button", { name: "Do not show this" });
  if (await coach.count()) await coach.click();

  // На компьютере карта догадки раскрывается наведением, как и в остальных
  // сценариях: кнопки «Открыть карту» там нет
  const guessMap = page.locator(".ol-viewport").nth(1);
  await guessMap.hover();
  await page.waitForTimeout(600);

  const box = await guessMap.boundingBox();
  expect(box).not.toBeNull();
  await page.mouse.click(box!.x + box!.width * 0.5, box!.y + box!.height * 0.45);

  await page.getByRole("button", { name: "Answer" }).click();
  const result = page.getByRole("dialog");
  await expect(result).toBeVisible();

  // Каталог написан по-русски, а игрок выбрал английский: ни названия места,
  // ни страны кириллицей в результате быть не должно
  await expect(result.getByText(/[А-Яа-я]/)).toHaveCount(0);
  await expect(result.getByRole("button", { name: /Next round|See the summary/ })).toBeVisible();
});
