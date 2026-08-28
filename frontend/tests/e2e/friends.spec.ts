/**
 * Друзья: двое обмениваются кодами и видят общий зачёт.
 *
 * Код здесь важнее списка: по имени игрока не найти намеренно.
 */

import { expect, test, type Page } from "@playwright/test";

import { open, register } from "./helpers";

/** Открыть раздел друзей и прочитать свой код. */
async function myCode(page: Page): Promise<string> {
  await open(page, "Друзья");

  // Список друзей приезжает запросом, и до его ответа код пуст
  const shown = page.locator("code").first();
  await expect(shown).toHaveText(/^[A-Z2-9]{6}$/);

  return (await shown.textContent()) ?? "";
}

test("двое добавляются по коду и попадают в общий зачёт", async ({ browser, page }) => {
  const host = await register(page);
  const code = await myCode(page);

  const friendContext = await browser.newContext();
  const friendPage = await friendContext.newPage();
  const guest = await register(friendPage);

  await open(friendPage, "Друзья");
  await friendPage.getByLabel("Код друга").fill(code);
  await friendPage.getByRole("button", { name: "Позвать" }).click();
  await expect(friendPage.getByText("ждёт ответа")).toBeVisible();

  // Заявка ждёт ответа у того, кого позвали
  await page.reload();
  await open(page, "Друзья");
  await expect(page.getByText("зовёт тебя")).toBeVisible();
  await page.getByRole("button", { name: "Принять" }).click();

  await expect(page.getByText(guest.name)).toBeVisible();
  await expect(page.getByText("зовёт тебя")).toBeHidden();

  // Зачёт среди друзей — отдельный пункт в выборе условий таблицы лидеров
  await open(page, "Таблица");
  await page.getByLabel(/Зачёт/).selectOption({ label: "Друзья" });
  await expect(page.getByText(host.name).first()).toBeVisible();

  await friendContext.close();
});

test("свой код в друзья не принимается", async ({ page }) => {
  await register(page);
  const code = await myCode(page);

  await page.getByLabel("Код друга").fill(code);
  await page.getByRole("button", { name: "Позвать" }).click();

  await expect(page.getByText("Это твой собственный код")).toBeVisible();
});
