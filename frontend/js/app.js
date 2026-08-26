/** Точка входа клиента: вход, меню и запуск партии. */

import { ApiError, auth, forgetSession, isAuthorized } from "./api.js";
import { quitGame, startGame } from "./game.js";
import {
    el,
    formatDistance,
    formatScore,
    segmented,
    setText,
    show,
    showError,
    showLoader,
    showScreen,
    toast,
} from "./ui.js";

const readRounds = segmented(el.optRounds);
const readExtent = segmented(el.optExtent);
const readDifficulty = segmented(el.optDifficulty);

let mode = "login";

// ── Вход ─────────────────────────────────────────────────────────────

function setMode(next) {
    mode = next;

    el.tabLogin.classList.toggle("is-active", mode === "login");
    el.tabRegister.classList.toggle("is-active", mode === "register");

    show(el.fieldName, mode === "register");
    setText(el.btnAuthSubmit, mode === "login" ? "Войти" : "Создать аккаунт");
    el.authPassword.autocomplete = mode === "login" ? "current-password" : "new-password";

    showError(el.authError, null);
}

async function handleAuthSubmit(event) {
    event.preventDefault();
    showError(el.authError, null);

    const email = el.authEmail.value.trim();
    const password = el.authPassword.value;

    if (!email || !password) {
        showError(el.authError, "Заполни email и пароль");
        return;
    }
    if (mode === "register" && password.length < 8) {
        showError(el.authError, "Пароль должен быть не короче 8 символов");
        return;
    }

    el.btnAuthSubmit.disabled = true;
    try {
        const user =
            mode === "login"
                ? await auth.login(email, password)
                : await auth.register(email, password, el.authName.value.trim());

        enterMenu(user);
    } catch (error) {
        showError(el.authError, describe(error));
    } finally {
        el.btnAuthSubmit.disabled = false;
    }
}

async function handleGuest() {
    el.btnGuest.disabled = true;
    try {
        enterMenu(await auth.guest());
    } catch (error) {
        showError(el.authError, describe(error));
    } finally {
        el.btnGuest.disabled = false;
    }
}

function handleLogout() {
    forgetSession();
    show(el.topbar, false);
    setMode("login");
    showScreen("screenAuth");
}

function describe(error) {
    if (error instanceof ApiError) return error.detail;
    return "Сервер недоступен. Попробуй ещё раз";
}

// ── Меню ─────────────────────────────────────────────────────────────

/** Обновить имя игрока и статистику, не трогая текущий экран. */
function applyProfile(user) {
    show(el.topbar, true);
    setText(el.playerName, user.display_name ?? user.username);

    setText(el.mGames, formatScore(user.games_played));
    setText(el.mRounds, formatScore(user.total_rounds));
    setText(el.mBest, formatScore(user.best_score));
    setText(
        el.mDistance,
        user.average_distance === null ? "—" : formatDistance(user.average_distance),
    );
}

function enterMenu(user) {
    applyProfile(user);
    showError(el.menuError, null);
    showScreen("screenMenu");
}

/**
 * Подтянуть статистику после партии.
 *
 * Экран не переключается: игрок в этот момент смотрит итоги, и уводить его
 * оттуда нельзя.
 */
async function refreshProfile() {
    try {
        applyProfile(await auth.me());
    } catch {
        // Профиль не обновился — цифры в меню просто останутся прежними
    }
}

async function handleStart() {
    const difficulty = readDifficulty();

    showError(el.menuError, null);
    el.btnStart.disabled = true;

    try {
        await startGame(
            {
                rounds_total: Number(readRounds()),
                view_extent_km: Number(readExtent()),
                difficulty: difficulty === "" ? null : Number(difficulty),
            },
            { onFinish: refreshProfile },
        );
    } catch (error) {
        showError(el.menuError, describe(error));
        showScreen("screenMenu");
    } finally {
        el.btnStart.disabled = false;
    }
}

async function handleQuit() {
    if (!confirm("Завершить партию досрочно?")) return;

    try {
        await quitGame();
    } catch (error) {
        toast(describe(error));
    }
}

// ── Запуск ───────────────────────────────────────────────────────────

el.tabLogin.addEventListener("click", () => setMode("login"));
el.tabRegister.addEventListener("click", () => setMode("register"));
el.authForm.addEventListener("submit", handleAuthSubmit);
el.btnGuest.addEventListener("click", handleGuest);
el.btnLogout.addEventListener("click", handleLogout);
el.btnStart.addEventListener("click", handleStart);
el.btnQuit.addEventListener("click", handleQuit);
el.btnPlayAgain.addEventListener("click", () => showScreen("screenMenu"));

async function boot() {
    setMode("login");

    if (!isAuthorized()) {
        showScreen("screenAuth");
        return;
    }

    showLoader(true, "Восстанавливаем сессию…");
    try {
        enterMenu(await auth.me());
    } catch {
        forgetSession();
        showScreen("screenAuth");
    } finally {
        showLoader(false);
    }
}

boot();
