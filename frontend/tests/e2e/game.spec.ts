/**
 * Сквозной сценарий: регистрация, партия, итоги, таблица лидеров.
 *
 * Ожидает поднятые бэкенд и фронтенд с загруженными зонами.
 */

import { expect, test, type Page } from "@playwright/test";

/** Уникальный игрок на каждый прогон: база между запусками не чистится. */
function newPlayer() {
  const suffix = Math.random().toString(36).slice(2, 8);
  return {
    email: `e2e-${suffix}@example.com`,
    password: "e2e password long enough",
    name: `Игрок ${suffix.slice(0, 3).toUpperCase()}`,
  };
}

async function register(page: Page) {
  const player = newPlayer();

  await page.goto("/");
  await page.getByRole("tab", { name: "Регистрация" }).click();
  await page.getByPlaceholder("you@example.com").fill(player.email);
  await page.getByPlaceholder(/Не короче/).fill(player.password);
  await page.getByPlaceholder("Как тебя показывать").fill(player.name);
  await page.getByRole("button", { name: "Создать аккаунт" }).click();

  await expect(page.getByRole("button", { name: "Начать игру" })).toBeVisible();
  return player;
}

/** Поставить точку на карте догадки и ответить. */
async function answerRound(page: Page) {
  const guessMap = page.locator(".ol-viewport").nth(1);

  // Наведение раскрывает панель, после чего меняются её размеры
  await guessMap.hover();
  await page.waitForTimeout(500);

  const box = await guessMap.boundingBox();
  expect(box).not.toBeNull();
  await page.mouse.click(box!.x + box!.width * 0.5, box!.y + box!.height * 0.45);

  await page.getByRole("button", { name: "Ответить" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
}

test("партия от регистрации до итогов", async ({ page }) => {
  await register(page);

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
  await expect(page.getByRole("button", { name: "Играть снова" })).toBeVisible();
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

  await page.getByRole("radio", { name: "3", exact: true }).first().click();
  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  for (let round = 1; round <= 3; round += 1) {
    await answerRound(page);
    const next = round === 3 ? "Посмотреть итоги" : "Следующий раунд";
    await page.getByRole("dialog").getByRole("button", { name: next }).click();
  }

  await page.getByRole("button", { name: "В меню" }).click();

  await expect(page.getByText("Последние партии")).toBeVisible();
  await expect(page.getByText(player.name, { exact: false }).first()).toBeVisible();
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

  await expect(page.getByText("Челлендж дня")).toBeVisible();
  await page.getByRole("button", { name: "Играть челлендж" }).click();

  await expect(page.getByRole("progressbar")).toBeVisible();
  await expect(page.locator("canvas").first()).toBeVisible();

  // Челлендж всегда из пяти раундов
  await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuemax", "5");

  for (let round = 1; round <= 5; round += 1) {
    await answerRound(page);
    const next = round === 5 ? "Посмотреть итоги" : "Следующий раунд";
    await page.getByRole("dialog").getByRole("button", { name: next }).click();
  }

  await page.getByRole("button", { name: "В меню" }).click();

  await expect(page.getByText("Твой результат сегодня")).toBeVisible();
  await expect(page.getByRole("button", { name: "Играть челлендж" })).toHaveCount(0);
});

test("результатом можно поделиться", async ({ context, page }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await register(page);

  await page.getByRole("radio", { name: "3", exact: true }).first().click();
  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  for (let round = 1; round <= 3; round += 1) {
    await answerRound(page);
    const next = round === 3 ? "Посмотреть итоги" : "Следующий раунд";
    await page.getByRole("dialog").getByRole("button", { name: next }).click();
  }

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
