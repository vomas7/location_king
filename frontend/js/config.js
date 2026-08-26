/** Настройки клиента, приходящие из config.js. */

const runtime = window.__CONFIG__ ?? {};

/** База API. Пустая строка означает тот же origin, что и у страницы. */
export const API_BASE = String(runtime.apiBase ?? "").replace(/\/+$/, "");

/** Ключ, под которым в браузере лежат токены. */
export const STORAGE_KEY = "location-king:session";

/** Пороги для словесной оценки результата раунда. */
export const SCORE_TIERS = [
    { min: 0.98, label: "В яблочко" },
    { min: 0.85, label: "Отлично" },
    { min: 0.6, label: "Хорошо" },
    { min: 0.35, label: "Неплохо" },
    { min: 0.1, label: "Мимо" },
    { min: 0, label: "Совсем не туда" },
];
