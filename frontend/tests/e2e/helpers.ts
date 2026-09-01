/** Общие шаги сценариев: регистрация игрока и ответ на раунд. */

import { expect, type Page } from "@playwright/test";

export interface Player {
  email: string;
  password: string;
  name: string;
}

/**
 * Свой адрес каждому игроку.
 *
 * Регистрации ограничены по адресу клиента — тридцать в час, и это главное
 * свойство игры, а не помеха. Но прогон сценариев — это тридцать разных
 * людей за три минуты, и с одного адреса он упирается в лимит и начинает
 * падать в CI вместо того, чтобы находить ошибки. В жизни за этими
 * тридцатью людьми стоят тридцать адресов, поэтому и здесь каждому
 * браузерному контексту достаётся свой.
 *
 * В бою заголовок проставляет nginx и клиентский подделать не даёт; в
 * тестах бэкенд открыт напрямую, и подделать его может только сам тест. Сам
 * лимит проверяется там, где это и надо делать, — в
 * `backend/tests/test_rate_limit.py`.
 *
 * Счётчика хватает, потому что воркер один: он задан в playwright.config.ts.
 * Диапазон 203.0.113.0/24 отведён под документацию и примеры.
 */
let players = 0;

function nextAddress(): string {
  players += 1;
  return `203.0.113.${String((players % 254) + 1)}`;
}

/** Выдать вкладке свой адрес. Нужно всему, что пробует зарегистрироваться. */
export async function ownAddress(page: Page): Promise<void> {
  await page.context().setExtraHTTPHeaders({ "X-Forwarded-For": nextAddress() });
}

/** Уникальный игрок на каждый прогон: база между запусками не чистится. */
export function newPlayer(): Player {
  const suffix = Math.random().toString(36).slice(2, 8);
  return {
    email: `e2e-${suffix}@example.com`,
    password: "e2e password long enough",
    name: `Игрок ${suffix.slice(0, 3).toUpperCase()}`,
  };
}

export async function register(page: Page): Promise<Player> {
  const player = newPlayer();

  await ownAddress(page);

  await page.goto("/");
  await page.getByRole("tab", { name: "Регистрация" }).click();
  await page.getByPlaceholder("you@example.com").fill(player.email);
  await page.getByPlaceholder(/Не короче/).fill(player.password);
  await page.getByPlaceholder("Как тебя показывать").fill(player.name);
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Создать аккаунт" }).click();

  await expect(page.getByRole("button", { name: "Начать игру" })).toBeVisible();
  return player;
}

/**
 * Открыть режим игры или раздел в меню: и то и другое — вкладки, и раскрыта
 * всегда ровно одна.
 */
export async function open(page: Page, name: string): Promise<void> {
  await page.getByRole("tab", { name }).click();
}

/** Поставить точку на карте догадки и ответить. */
export async function answerRound(page: Page): Promise<void> {
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

/**
 * Выбрать страну на карте и ответить.
 *
 * Куда именно ткнуть, заранее не известно: карта мира на весь океан, а по
 * океану выбирать нечего. Поэтому пробуем несколько точек по суше, пока
 * страна не выберется, — так же, как это делает игрок.
 */
export async function answerCountryRound(page: Page): Promise<void> {
  const guessMap = page.locator(".ol-viewport").nth(1);

  await guessMap.hover();
  await page.waitForTimeout(500);

  const box = await guessMap.boundingBox();
  expect(box).not.toBeNull();

  const answer = page.getByRole("button", { name: "Ответить" });

  // Африка, Евразия, Южная Америка: хоть куда-то попадём
  const spots: [number, number][] = [
    [0.55, 0.6],
    [0.62, 0.4],
    [0.32, 0.7],
  ];

  for (const [x, y] of spots) {
    await page.mouse.click(box!.x + box!.width * x, box!.y + box!.height * y);
    await page.waitForTimeout(300);

    if (await answer.isEnabled()) break;
  }

  await expect(answer).toBeEnabled();
  await answer.click();
  await expect(page.getByRole("dialog")).toBeVisible();
}

/** Доиграть партию из указанного числа раундов до экрана итогов. */
export async function playRounds(page: Page, rounds: number): Promise<void> {
  for (let round = 1; round <= rounds; round += 1) {
    await answerRound(page);
    const next = round === rounds ? "Посмотреть итоги" : "Следующий раунд";
    await page.getByRole("dialog").getByRole("button", { name: next }).click();
  }
}
