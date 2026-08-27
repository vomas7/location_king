/** Эндпоинты API. Тонкая типизированная обёртка над клиентом. */

import { request } from "~/api/client";
import { setTokens } from "~/api/tokens";
import type {
  AuthResponse,
  DailyChallenge,
  GuessResponse,
  Leaderboard,
  LeaderboardMetric,
  MatchList,
  MatchView,
  SessionHistory,
  SessionState,
  StartSessionOptions,
  UserProfile,
  Zone,
} from "~/api/types";

async function authenticate(path: string, body: unknown): Promise<UserProfile> {
  const result = await request<AuthResponse>(path, { method: "POST", body, skipRefresh: true });
  setTokens(result.tokens);
  return result.user;
}

export const auth = {
  register: (email: string, password: string, displayName: string) =>
    authenticate("/api/auth/register", {
      email,
      password,
      display_name: displayName === "" ? null : displayName,
    }),

  login: (email: string, password: string) => authenticate("/api/auth/login", { email, password }),

  me: () => request<UserProfile>("/api/auth/me"),
};

export const game = {
  start: (options: StartSessionOptions) =>
    request<SessionState>("/api/sessions", { method: "POST", body: options }),

  current: () => request<SessionState | null>("/api/sessions/current"),

  session: (sessionId: string) => request<SessionState>(`/api/sessions/${sessionId}`),

  finish: (sessionId: string) =>
    request<SessionState>(`/api/sessions/${sessionId}/finish`, { method: "POST" }),

  timeout: (roundId: number) =>
    request<GuessResponse>(`/api/rounds/${String(roundId)}/timeout`, { method: "POST" }),

  guess: (roundId: number, longitude: number, latitude: number) =>
    request<GuessResponse>(`/api/rounds/${String(roundId)}/guess`, {
      method: "POST",
      body: { longitude, latitude },
    }),

  history: (limit = 10) => request<SessionHistory>(`/api/sessions?limit=${String(limit)}`),
};

export const challenge = {
  today: () => request<DailyChallenge>("/api/challenge/today"),

  start: () => request<SessionState>("/api/challenge/today/start", { method: "POST" }),
};

export const matches = {
  create: (options: StartSessionOptions) =>
    request<MatchView>("/api/matches", { method: "POST", body: options }),

  /** Комнаты, созданные игроком. */
  mine: () => request<MatchList>("/api/matches/mine"),

  get: (code: string) => request<MatchView>(`/api/matches/${encodeURIComponent(code)}`),

  join: (code: string) =>
    request<SessionState>(`/api/matches/${encodeURIComponent(code)}/join`, { method: "POST" }),

  close: (code: string) =>
    request<MatchView>(`/api/matches/${encodeURIComponent(code)}/close`, { method: "POST" }),
};

export const leaderboard = {
  top: (metric: LeaderboardMetric, limit = 20) =>
    request<Leaderboard>(`/api/leaderboard?metric=${metric}&limit=${String(limit)}`),
};

export const zones = {
  /** query — строка вида "continent=europe&difficulty=3". */
  list: (query = "") => request<Zone[]>(`/api/zones${query === "" ? "" : `?${query}`}`),
};
