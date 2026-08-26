/**
 * Ход игры: партия, раунд, догадка.
 *
 * Здесь нет ни одной проверки правил — их делает сервер. Клиент только
 * показывает то, что сервер разрешил показать.
 */

import { ApiError, game as api } from "./api.js";
import { createGuessMap, createResultMap, createSatelliteMap } from "./map.js";
import {
    el,
    formatDistance,
    formatExtent,
    formatScore,
    plural,
    renderRounds,
    scoreTier,
    setText,
    show,
    showLoader,
    showScreen,
    toast,
} from "./ui.js";

const state = {
    session: null,
    round: null,
    guess: null,
    results: [],
    satellite: null,
    guessMap: null,
    resultMap: null,
    onFinish: null,
};

/** Начать партию с заданными настройками. */
export async function startGame(options, { onFinish }) {
    state.onFinish = onFinish;
    state.results = [];

    showLoader(true, "Выбираем место…");
    try {
        const response = await api.startSession(options);
        state.session = response.session;

        showScreen("screenGame");
        show(el.gameStats, true);
        show(el.btnQuit, true);

        setUpMaps();
        openRound(response.current_round);
    } finally {
        showLoader(false);
    }
}

/** Завершить партию досрочно. */
export async function quitGame() {
    if (!state.session) return;

    showLoader(true, "Подводим итоги…");
    try {
        const response = await api.finishSession(state.session.id);
        state.session = response.session;
        state.results = response.results;
        finish();
    } finally {
        showLoader(false);
    }
}

function setUpMaps() {
    if (state.guessMap) return;

    state.guessMap = createGuessMap("guessMap", (point) => {
        state.guess = point;
        el.btnSubmit.disabled = false;
        setText(el.guessHint, "Точка поставлена — можно отвечать");
    });

    state.resultMap = createResultMap("resultMap");

    el.btnSubmit.addEventListener("click", submitGuess);
    el.btnNext.addEventListener("click", nextRound);
    el.btnGuessToggle.addEventListener("click", toggleGuessPanel);
}

function openRound(round) {
    state.round = round;
    state.guess = null;

    el.btnSubmit.disabled = true;
    setText(el.guessHint, "Кликни по карте, чтобы поставить точку");
    setText(el.statRound, `${round.index} / ${state.session.rounds_total}`);
    setText(el.statScore, formatScore(state.session.total_score));
    setText(el.extentLabel, `участок ~${formatExtent(round.view_extent_km)}`);
    setText(el.attribution, round.attribution);

    state.satellite?.destroy();
    state.satellite = createSatelliteMap("satelliteMap", round);

    state.guessMap.clear();
    setGuessPanelOpen(false);
}

async function submitGuess() {
    if (!state.guess || !state.round) return;

    el.btnSubmit.disabled = true;
    showLoader(true, "Считаем расстояние…");

    try {
        const response = await api.submitGuess(
            state.round.id,
            state.guess.longitude,
            state.guess.latitude,
        );

        state.session = response.session;
        state.results.push(response.result);
        state.nextRound = response.next_round;

        showRoundResult(response.result, response.is_session_finished);
    } catch (error) {
        el.btnSubmit.disabled = false;
        toast(error instanceof ApiError ? error.detail : "Не удалось отправить догадку");
    } finally {
        showLoader(false);
    }
}

function showRoundResult(result, isFinished) {
    setText(el.resultTier, scoreTier(result.score, result.max_score));
    setText(el.resultScore, formatScore(result.score));
    setText(el.resultDistance, formatDistance(result.distance_km));
    setText(el.resultAccuracy, `${Number(result.accuracy ?? 0).toFixed(0)}%`);
    setText(el.resultZone, result.zone.name);
    setText(
        el.resultZoneMeta,
        [result.zone.country, result.zone.region, result.zone.difficulty_name]
            .filter(Boolean)
            .join(" · "),
    );
    setText(el.statScore, formatScore(state.session.total_score));

    setText(el.btnNext, isFinished ? "Посмотреть итоги" : "Следующий раунд");

    show(el.overlayRound, true);
    state.resultMap.show(result.target, result.guess);
}

function nextRound() {
    show(el.overlayRound, false);

    if (state.nextRound) {
        openRound(state.nextRound);
        state.nextRound = null;
        return;
    }

    finish();
}

function finish() {
    state.satellite?.destroy();
    state.satellite = null;

    show(el.gameStats, false);
    show(el.btnQuit, false);

    const played = state.results.length;
    setText(el.summaryScore, formatScore(state.session.total_score));
    setText(
        el.summarySubtitle,
        played === 0
            ? "Ни одного раунда не сыграно"
            : `${played} ${plural(played, "раунд", "раунда", "раундов")} · ` +
              `в среднем ${formatScore(Math.round(state.session.total_score / played))} за раунд`,
    );

    renderRounds(el.summaryRounds, state.results);
    showScreen("screenSummary");

    state.session = null;
    state.round = null;
    state.onFinish?.();
}

// ── Панель карты догадки ─────────────────────────────────────────────

function toggleGuessPanel() {
    setGuessPanelOpen(!el.guessPanel.classList.contains("is-open"));
}

function setGuessPanelOpen(open) {
    el.guessPanel.classList.toggle("is-open", open);
    el.btnGuessToggle.setAttribute("aria-expanded", String(open));

    if (open) {
        // Карта должна пересчитать размеры после раскрытия панели
        requestAnimationFrame(() => state.guessMap?.refresh());
    }
}
