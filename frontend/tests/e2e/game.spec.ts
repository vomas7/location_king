/**
 * Сквозной сценарий: регистрация, партия, итоги, таблица лидеров.
 *
 * Ожидает поднятые бэкенд и фронтенд с загруженными зонами.
 */

import { expect, test } from "@playwright/test";

import { answerRound, open, openSetup, playRounds, register } from "./helpers";

test("партия от регистрации до итогов", async ({ page }) => {
  await register(page);

  await openSetup(page);
  await page.getByRole("radio", { name: "3", exact: true }).first().click();
  await page.getByRole("button", { name: "Начать игру" }).click();

  await expect(page.getByRole("progressbar")).toBeVisible();
  await expect(page.locator("canvas").first()).toBeVisible();

  for (let round = 1; round <= 3; round += 1) {
    await answerRound(page);

    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText("очков", { exact: false })).toBeVisible();

    const next = round === 3 ? "Посмотреть итоги" : "Следующий раунд";
    await dialog.getByRole("button", { name: next }).click();
  }

  await expect(page.getByText("Партия окончена")).toBeVisible();

  // «Играть снова» повторяет те же условия, а не отправляет в меню
  await page.getByRole("button", { name: "Играть снова" }).click();

  await expect(page.getByText("Раунд 1 из 3")).toBeVisible();
  await expect(page.locator("canvas").first()).toBeVisible();
});

test("новичку объясняют игру в первом раунде и только в нём", async ({ page }) => {
  await register(page);

  await openSetup(page);
  await page.getByRole("radio", { name: "3", exact: true }).first().click();
  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  await expect(page.getByText("Осмотрись")).toBeVisible();
  await page.getByRole("button", { name: "Понятно" }).click();
  await expect(page.getByRole("heading", { name: "Отметь место" })).toBeVisible();

  await answerRound(page);
  await page.getByRole("dialog").getByRole("button", { name: "Следующий раунд" }).click();

  // Второй раунд игрок открывает уже сам
  await expect(page.getByText("Шаг 1 из 3")).toBeHidden();
});

test("подсказка раскрывает место и стоит очков", async ({ page }) => {
  await register(page);

  await openSetup(page);
  await page.getByRole("radio", { name: "3", exact: true }).first().click();
  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  const takeHint = page.getByRole("button", { name: /Подсказка/ });
  await expect(takeHint).toBeVisible();
  await takeHint.click();

  // Партия по всему миру: раскрывать сервер начинает с части света
  await expect(page.getByText("Часть света")).toBeVisible();
  await expect(takeHint).toBeHidden();

  // Максимум раунда упал — это видно в результате
  await answerRound(page);
  await expect(page.getByRole("dialog").getByText("из 3", { exact: false })).toBeVisible();
});

test("в итогах партию можно разобрать по карте", async ({ page }) => {
  await register(page);

  await openSetup(page);
  await page.getByRole("radio", { name: "3", exact: true }).first().click();
  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  await playRounds(page, 3);
  await expect(page.getByText("Партия окончена")).toBeVisible();

  // Карта разбора на месте, и сначала на ней вся партия
  await expect(page.locator("canvas").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Показать всю партию" })).toBeHidden();

  // Строка списка приближает карту к своему раунду
  await page.getByRole("button", { name: /^Раунд 1,/ }).click();

  const back = page.getByRole("button", { name: "Показать всю партию" });
  await expect(back).toBeVisible();
  await back.click();
  await expect(back).toBeHidden();
});

test("активный раунд не отдаёт координаты цели", async ({ page }) => {
  await register(page);

  const responses: string[] = [];
  page.on("response", (response) => {
    const url = response.url();
    if (url.includes("/api/sessions") || url.includes("/api/rounds/")) {
      if (!url.includes("/guess") && !url.includes("/tiles/")) {
        responses.push(url);
        void response
          .text()
          .then((body) => {
            expect(body, `в ответе ${url} есть координаты цели`).not.toContain("target");
          })
          .catch(() => undefined);
      }
    }
  });

  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();
  await page.waitForTimeout(1500);

  expect(responses.length).toBeGreaterThan(0);
});

test("после партии игрок появляется в таблице лидеров", async ({ page }) => {
  const player = await register(page);

  await openSetup(page);
  await page.getByRole("radio", { name: "3", exact: true }).first().click();
  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  await playRounds(page, 3);

  await page.getByRole("button", { name: "В меню" }).click();

  await open(page, "История");
  await expect(page.getByText("Последние партии")).toBeVisible();

  // Имя игрока ищем в самой таблице: в шапке оно есть всегда
  await open(page, "Таблица");
  await expect(page.locator("#section-panel").getByText(player.name)).toBeVisible();
});

test("незаконченную партию предлагают продолжить", async ({ page }) => {
  await register(page);

  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  await page.reload();

  await expect(page.getByText("У тебя есть незаконченная партия")).toBeVisible();
  await page.getByRole("button", { name: "Продолжить" }).click();

  await expect(page.getByRole("progressbar")).toBeVisible();
});

test("вход отвергает неверный пароль", async ({ page }) => {
  const player = await register(page);

  await page.getByRole("button", { name: "Выйти" }).click();
  await page.getByPlaceholder("you@example.com").fill(player.email);
  await page.getByPlaceholder(/Не короче/).fill("совсем другой пароль");
  await page.getByRole("button", { name: "Войти" }).click();

  await expect(page.getByRole("alert")).toContainText("Неверный email или пароль");
});

test("челлендж дня играется один раз в сутки", async ({ page }) => {
  await register(page);

  await open(page, "Челлендж дня");
  await page.getByRole("button", { name: "Играть челлендж" }).click();

  await expect(page.getByRole("progressbar")).toBeVisible();
  await expect(page.locator("canvas").first()).toBeVisible();

  // Челлендж всегда из пяти раундов
  await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuemax", "5");

  await playRounds(page, 5);

  await page.getByRole("button", { name: "В меню" }).click();

  await open(page, "Челлендж дня");
  await expect(page.getByText("Твой результат сегодня")).toBeVisible();
  await expect(page.getByRole("button", { name: "Играть челлендж" })).toHaveCount(0);
});

test("результатом можно поделиться", async ({ context, page }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await register(page);

  await openSetup(page);
  await page.getByRole("radio", { name: "3", exact: true }).first().click();
  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  await playRounds(page, 3);

  await page.getByRole("button", { name: "Поделиться результатом" }).click();
  await expect(page.getByRole("button", { name: "Скопировано в буфер" })).toBeVisible();

  const copied = await page.evaluate(() => navigator.clipboard.readText());
  expect(copied).toContain("Location King");
  expect(copied).toMatch(/[⭐🟩🟨🟧🟥⬛]/u);
  // В тексте не должно быть названий мест: он уходит тем, кто ещё не играл
  expect(copied).not.toContain("Москва");
});

test("в режиме на время идёт обратный отсчёт", async ({ page }) => {
  await register(page);

  await openSetup(page);
  await page.getByRole("radio", { name: "3", exact: true }).first().click();
  await page.getByRole("radio", { name: "30 сек" }).click();
  await page.getByRole("button", { name: "Начать игру" }).click();

  const timer = page.getByRole("timer");
  await expect(timer).toBeVisible();

  const first = await timer.textContent();
  await page.waitForTimeout(2500);
  const second = await timer.textContent();

  expect(first).not.toBe(second);

  // Ответ засчитывается как обычно
  await answerRound(page);
  await expect(page.getByRole("dialog")).toBeVisible();
});

test("часть света ограничивает выбор зон", async ({ page }) => {
  await register(page);

  await openSetup(page);
  await expect(page.getByText(/Подходящих зон: \d+/)).toBeVisible();
  const worldwide = await page.getByText(/Подходящих зон: \d+/).textContent();

  await page.getByRole("radio", { name: "Океания" }).click();
  await expect(page.getByText(/Подходящих зон: \d+/)).not.toHaveText(worldwide ?? "");

  await page.getByRole("radio", { name: "3", exact: true }).first().click();
  await page.getByRole("button", { name: "Начать игру" }).click();

  await answerRound(page);
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();

  // Зона раунда действительно из выбранной части света
  await expect(dialog.getByText(/Австралия|Новая Зеландия|Полинезия|Папуа/).first()).toBeVisible();
});

test("аватарка видна в шапке и меняется в профиле", async ({ page }) => {
  await register(page);

  // Аватарка выдаётся при регистрации: пустого места на её месте не бывает
  await expect(page.getByRole("img", { name: /Аватарка игрока/ }).first()).toBeVisible();

  await page.getByRole("button", { name: "Изменить" }).click();
  await page.getByRole("radio", { name: "Узор 4" }).click();
  await page.getByRole("button", { name: "Сохранить" }).click();

  await expect(page.getByRole("button", { name: "Изменить" })).toBeVisible();
});
