/** Общие шаги сценариев: регистрация игрока и ответ на раунд. */

import { expect, type Page } from "@playwright/test";

export interface Player {
  email: string;
  password: string;
  name: string;
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

/** Развернуть условия одиночной партии: по умолчанию они свёрнуты в строку. */
export async function openSetup(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Настроить" }).click();
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

/** Доиграть партию из указанного числа раундов до экрана итогов. */
export async function playRounds(page: Page, rounds: number): Promise<void> {
  for (let round = 1; round <= rounds; round += 1) {
    await answerRound(page);
    const next = round === rounds ? "Посмотреть итоги" : "Следующий раунд";
    await page.getByRole("dialog").getByRole("button", { name: next }).click();
  }
}
