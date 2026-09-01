/**
 * Выбор языка.
 *
 * Русский — основной, но игру должно быть можно показать за пределами
 * русскоязычного интернета. Поэтому язык выбирается сам по языку браузера, а
 * переключить его можно из подвала — и выбор переживает перезагрузку.
 */

import { expect, test } from "@playwright/test";

test.describe("английский браузер", () => {
  test.use({ locale: "en-US" });

  test("сразу видит английскую страницу", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: /Find the spot/ })).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
  });

  test("переключается на русский и помнит выбор", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Русский" }).click();

    await expect(page.getByRole("heading", { name: /Найди точку/ })).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("lang", "ru");

    await page.reload();
    await expect(page.getByRole("heading", { name: /Найди точку/ })).toBeVisible();
  });
});

test("русский браузер видит русскую страницу", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: /Найди точку/ })).toBeVisible();
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
