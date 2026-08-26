/**
 * Клиент API.
 *
 * Токены хранятся в localStorage, access обновляется по refresh автоматически
 * при первом же 401. Наружу отдаются осмысленные ошибки, а не голые Response.
 */

import { API_BASE, STORAGE_KEY } from "./config.js";

export class ApiError extends Error {
    constructor(status, detail) {
        super(detail);
        this.status = status;
        this.detail = detail;
    }
}

let tokens = readTokens();

function readTokens() {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY)) ?? null;
    } catch {
        return null;
    }
}

function writeTokens(value) {
    tokens = value;
    try {
        if (value) {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
        } else {
            localStorage.removeItem(STORAGE_KEY);
        }
    } catch {
        // Приватный режим браузера: играем без запоминания сессии
    }
}

export function isAuthorized() {
    return Boolean(tokens?.access_token);
}

export function forgetSession() {
    writeTokens(null);
}

/** Заголовки авторизации — нужны и прокси тайлов. */
export function authHeaders() {
    return tokens?.access_token ? { Authorization: `Bearer ${tokens.access_token}` } : {};
}

async function parseError(response) {
    const fallback = `Ошибка ${response.status}`;
    try {
        const body = await response.json();
        if (typeof body.detail === "string") return body.detail;
        if (Array.isArray(body.detail)) return body.detail.map((e) => e.msg).join("; ");
        return fallback;
    } catch {
        return fallback;
    }
}

async function refreshTokens() {
    if (!tokens?.refresh_token) return false;

    const response = await fetch(`${API_BASE}/api/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: tokens.refresh_token }),
    });

    if (!response.ok) {
        writeTokens(null);
        return false;
    }

    writeTokens(await response.json());
    return true;
}

/** Запрос к API с авторизацией и одной повторной попыткой после обновления токена. */
export async function request(path, { method = "GET", body, raw = false, retry = true } = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        method,
        headers: {
            ...authHeaders(),
            ...(body === undefined ? {} : { "Content-Type": "application/json" }),
        },
        body: body === undefined ? undefined : JSON.stringify(body),
    });

    if (response.status === 401 && retry && (await refreshTokens())) {
        return request(path, { method, body, raw, retry: false });
    }

    if (!response.ok) {
        throw new ApiError(response.status, await parseError(response));
    }

    if (raw) return response;
    return response.status === 204 ? null : response.json();
}

// ── Аутентификация ───────────────────────────────────────────────────

async function authenticate(path, body) {
    const result = await request(path, { method: "POST", body, retry: false });
    writeTokens(result.tokens);
    return result.user;
}

export const auth = {
    register: (email, password, displayName) =>
        authenticate("/api/auth/register", {
            email,
            password,
            display_name: displayName || null,
        }),

    login: (email, password) => authenticate("/api/auth/login", { email, password }),

    guest: () => authenticate("/api/auth/guest", undefined),

    me: () => request("/api/auth/me"),
};

// ── Игра ─────────────────────────────────────────────────────────────

export const game = {
    startSession: (options) => request("/api/sessions", { method: "POST", body: options }),

    getSession: (sessionId) => request(`/api/sessions/${sessionId}`),

    finishSession: (sessionId) =>
        request(`/api/sessions/${sessionId}/finish`, { method: "POST" }),

    submitGuess: (roundId, longitude, latitude) =>
        request(`/api/rounds/${roundId}/guess`, {
            method: "POST",
            body: { longitude, latitude },
        }),
};

/** Абсолютный адрес тайла раунда. */
export function tileUrl(template, z, x, y) {
    return `${API_BASE}${template}`
        .replace("{z}", z)
        .replace("{x}", x)
        .replace("{y}", y);
}
