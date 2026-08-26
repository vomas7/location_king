/** Работа с DOM: экраны, тексты, мелкие виджеты. */

import { SCORE_TIERS } from "./config.js";

/** Все элементы, к которым обращается приложение. */
export const el = new Proxy(
    {},
    {
        get: (cache, id) => {
            if (!(id in cache)) cache[id] = document.getElementById(id);
            return cache[id];
        },
    },
);

const SCREENS = ["screenAuth", "screenMenu", "screenGame", "screenSummary"];

/** Показать один экран, спрятав остальные. */
export function showScreen(name) {
    for (const id of SCREENS) {
        el[id].hidden = id !== name;
    }
}

export function show(element, visible = true) {
    element.hidden = !visible;
}

export function setText(element, text) {
    element.textContent = text;
}

export function showLoader(visible, text = "Ищем место…") {
    el.loaderText.textContent = text;
    el.loader.hidden = !visible;
}

let toastTimer = null;

/** Короткое сообщение поверх интерфейса. */
export function toast(message) {
    el.toast.textContent = message;
    el.toast.hidden = false;

    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
        el.toast.hidden = true;
    }, 4000);
}

export function showError(element, message) {
    element.textContent = message ?? "";
    element.hidden = !message;
}

// ── Форматирование ───────────────────────────────────────────────────

export function formatScore(value) {
    return Number(value).toLocaleString("ru-RU");
}

/** Расстояние: метры под километром, километры дальше. */
export function formatDistance(km) {
    const value = Number(km);

    if (!Number.isFinite(value)) return "—";
    if (value < 1) return `${Math.round(value * 1000)} м`;
    if (value < 100) return `${value.toFixed(1)} км`;

    return `${Math.round(value).toLocaleString("ru-RU")} км`;
}

export function formatExtent(km) {
    const value = Number(km);
    return value < 10 ? `${value.toFixed(1)} км` : `${Math.round(value)} км`;
}

/** Словесная оценка раунда по доле набранных очков. */
export function scoreTier(score, maxScore) {
    const ratio = maxScore > 0 ? score / maxScore : 0;
    return SCORE_TIERS.find((tier) => ratio >= tier.min).label;
}

/** Правильная форма слова «раунд» после числительного. */
export function plural(count, one, few, many) {
    const mod10 = count % 10;
    const mod100 = count % 100;

    if (mod10 === 1 && mod100 !== 11) return one;
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;

    return many;
}

// ── Переключатели ────────────────────────────────────────────────────

/** Сегментированный переключатель: возвращает функцию чтения значения. */
export function segmented(container) {
    container.addEventListener("click", (event) => {
        const button = event.target.closest(".segmented__item");
        if (!button) return;

        for (const item of container.querySelectorAll(".segmented__item")) {
            item.classList.toggle("is-active", item === button);
        }
    });

    return () => container.querySelector(".segmented__item.is-active")?.dataset.value ?? "";
}

// ── Списки ───────────────────────────────────────────────────────────

/** Отрисовать итоги раундов в списке. */
export function renderRounds(container, results) {
    container.replaceChildren(
        ...results.map((result) => {
            const item = document.createElement("li");
            item.className = "round";

            const place = document.createElement("div");
            place.className = "round__place";
            place.textContent = result.zone.name;

            const distance = document.createElement("span");
            distance.className = "round__distance";
            distance.textContent = formatDistance(result.distance_km);

            const score = document.createElement("span");
            score.className = "round__score";
            score.textContent = formatScore(result.score);

            const bar = document.createElement("div");
            bar.className = "round__bar";
            const fill = document.createElement("i");
            fill.style.width = `${Math.round((result.score / result.max_score) * 100)}%`;
            bar.append(fill);

            item.append(place, distance, score, bar);
            return item;
        }),
    );
}
