/**
 * Собрать public/config.js из переменных окружения перед сборкой.
 *
 * Файл читается браузером как есть, поэтому реквизиты оператора не нужно
 * держать в репозитории: их задают в .env, а docker-compose передаёт их сюда
 * аргументами сборки. Запускается только в образе — версия из репозитория
 * остаётся дефолтом для разработки.
 */

import { writeFileSync } from "node:fs";
import { fileURLToPath, URL } from "node:url";

const TARGET = fileURLToPath(new URL("../public/config.js", import.meta.url));

const config = {
  // Пусто — API живёт на том же origin, что и страница: без mixed content и CORS
  apiBase: "",
  operator: {
    name: (process.env.OPERATOR_NAME ?? "").trim(),
    email: (process.env.OPERATOR_EMAIL ?? "").trim(),
  },
};

writeFileSync(
  TARGET,
  "// Собран scripts/make-config.mjs при сборке образа из переменных .env.\n" +
    "// Правки здесь потеряются: меняйте OPERATOR_NAME и OPERATOR_EMAIL в .env.\n" +
    `window.__CONFIG__ = ${JSON.stringify(config, null, 2)};\n`,
);

console.log(`config.js собран, оператор: ${config.operator.name || "не указан"}`);
