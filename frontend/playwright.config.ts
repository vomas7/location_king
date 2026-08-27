import { defineConfig, devices } from "@playwright/test";

/**
 * Сценарии в браузере.
 *
 * Ожидают поднятое приложение: `make dev` или `npm run dev` вместе с бэкендом.
 * Адрес переопределяется переменной E2E_BASE_URL.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",

  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:5173",
    // Запасной путь к браузеру: в окружениях, где Chromium уже стоит отдельно,
    // качать его ещё раз незачем
    ...(process.env.PLAYWRIGHT_CHROMIUM_PATH
      ? { launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH } }
      : {}),
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },

  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
