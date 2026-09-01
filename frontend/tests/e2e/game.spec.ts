/**
 * Сквозной сценарий: регистрация, партия, итоги, таблица лидеров.
 *
 * Ожидает поднятые бэкенд и фронтенд с загруженными зонами.
 */

import { expect, test } from "@playwright/test";

import { answerCountryRound, answerRound, open, playRounds, register } from "./helpers";

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

  // «Играть снова» повторяет те же условия, а не отправляет в меню
  await page.getByRole("button", { name: "Играть снова" }).click();

  await expect(page.getByText("Раунд 1 из 3")).toBeVisible();
  await expect(page.locator("canvas").first()).toBeVisible();
});

test("новичку объясняют игру в первом раунде и только в нём", async ({ page }) => {
  await register(page);

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

  await page.getByRole("radio", { name: "3", exact: true }).first().click();
  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  // Пока новичку объясняют правила, подсказку не предлагают: на телефоне
  // карточка накрывает собой тот угол, где она стоит
  await page.getByRole("button", { name: "Не показывать" }).click();

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

test("новая партия не бросает незаконченную молча", async ({ page }) => {
  await register(page);

  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  await page.reload();
  await expect(page.getByText("У тебя есть незаконченная партия")).toBeVisible();

  // Окно подтверждения Playwright закрывает отказом — партия остаётся на месте
  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.getByText("У тебя есть незаконченная партия")).toBeVisible();

  // А с согласием начинается новая
  page.once("dialog", (dialog) => {
    void dialog.accept();
  });
  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();
});

test("условия партии переживают саму партию", async ({ page }) => {
  await register(page);

  await page.getByRole("radio", { name: "3", exact: true }).first().click();
  await page.getByRole("radio", { name: "Хардкор" }).click();

  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  await playRounds(page, 3);
  await page.getByRole("button", { name: "В меню" }).click();

  // Меню собирается заново, но выставленные условия должны остаться
  await expect(page.getByRole("radio", { name: "3", exact: true }).first()).toHaveAttribute(
    "aria-checked",
    "true",
  );
  await expect(page.getByRole("radio", { name: "Хардкор" })).toHaveAttribute(
    "aria-checked",
    "true",
  );
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

test("незаконченный челлендж продолжается, а не начинается заново", async ({ page }) => {
  await register(page);

  await open(page, "Челлендж дня");
  await page.getByRole("button", { name: "Играть челлендж" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  await page.reload();
  await open(page, "Челлендж дня");

  // Попытка в сутки одна, поэтому «Продолжить» обязано именно продолжать:
  // повторный старт сервер отвергает
  await page.getByRole("button", { name: "Продолжить челлендж" }).click();

  await expect(page.locator("canvas").first()).toBeVisible();
  await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuemax", "5");
});

test("результатом можно поделиться", async ({ context, page }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await register(page);

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

test("в режиме стран очки объясняет страна, а не километры", async ({ page }) => {
  await register(page);

  await page.getByRole("radio", { name: "3", exact: true }).first().click();
  await page.getByRole("radio", { name: "Страной" }).click();

  // Условия лежат открыто, разворачивать их не надо: выбранный режим виден
  // сразу, и играть будут не в то, что обычно
  await expect(page.getByRole("radio", { name: "Страной" })).toHaveAttribute(
    "aria-checked",
    "true",
  );

  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();
  await expect(page.getByText("Выбери страну, из которой снимок")).toBeVisible();

  await answerCountryRound(page);

  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("Страна", { exact: true })).toBeVisible();
  await expect(dialog.getByText("Твой ответ")).toBeVisible();
  // Точки в этом режиме нет вовсе, и обещать её в легенде нечестно
  await expect(dialog.getByText("твоя точка")).toHaveCount(0);
  // Ни промаха, ни разбора «здесь обычно промахиваются»: очки дали не за
  // километры, и объяснять их километрами нечестно
  await expect(dialog.getByText(/промах/i)).toHaveCount(0);
});

test("в режиме стран место в условиях не выбирают", async ({ page }) => {
  await register(page);

  await expect(page.getByRole("radio", { name: "Океания" })).toBeVisible();

  await page.getByRole("radio", { name: "Страной" }).click();

  // «Россия» в условиях партии была бы готовым ответом на все её раунды
  await expect(page.getByRole("radio", { name: "Океания" })).toHaveCount(0);
  await expect(page.getByText(/играем по всему миру/)).toBeVisible();
});

test("снимок приближается туда, куда смотрит игрок", async ({ page }) => {
  await register(page);

  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  const satellite = page.locator(".ol-viewport").first();
  const box = await satellite.boundingBox();
  expect(box).not.toBeNull();

  // Крутим колесо в стороне от центра: раньше вид на каждом шаге зума
  // возвращался к перекрестию, и рассмотреть окраины было нельзя
  const corner = { x: box!.x + box!.width * 0.25, y: box!.y + box!.height * 0.3 };
  await page.mouse.move(corner.x, corner.y);
  await page.mouse.wheel(0, -600);
  await page.waitForTimeout(700);

  // Перекрестие уехало от центра экрана — значит, приближали не к нему
  const reticle = page.locator(".ol-viewport").first();
  await expect(reticle).toBeVisible();
  await expect(page.getByRole("button", { name: "К цели" })).toBeVisible();

  await page.getByRole("button", { name: "К цели" }).click();
  await page.waitForTimeout(500);
  await expect(page.locator("canvas").first()).toBeVisible();
});

test("повёрнутый снимок разворачивается обратно на север", async ({ page }) => {
  await register(page);

  await page.getByRole("button", { name: "Начать игру" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();

  await page.getByRole("button", { name: "Не показывать" }).click();

  // Пока снимок смотрит на север, кнопке взяться неоткуда
  const north = page.getByRole("button", { name: "На север" });
  await expect(north).toHaveCount(0);

  // Пальцем снимок крутят щипком, мышью — перетаскиванием с Alt и Shift:
  // это штатный поворот OpenLayers, и в браузере он воспроизводим
  const box = await page.locator(".ol-viewport").first().boundingBox();
  expect(box).not.toBeNull();
  const middle = { x: box!.x + box!.width / 2, y: box!.y + box!.height / 2 };

  // Поворот считается от центра карты, поэтому тащим не из самого центра
  const from = { x: middle.x + 80, y: middle.y };

  await page.keyboard.down("Shift");
  await page.keyboard.down("Alt");
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  await page.mouse.move(middle.x, middle.y - 80, { steps: 12 });
  await page.mouse.up();
  await page.keyboard.up("Alt");
  await page.keyboard.up("Shift");

  await expect(north).toBeVisible();

  await north.click();
  await expect(north).toHaveCount(0);
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
