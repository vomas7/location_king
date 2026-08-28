/** Эндпоинты API. Тонкая типизированная обёртка над клиентом. */

import { request } from "~/api/client";
import { setTokens } from "~/api/tokens";
import type {
  AuthResponse,
  DailyChallenge,
  DuelFormat,
  DuelSearch,
  Friend,
  FriendList,
  GuessResponse,
  Leaderboard,
  LeaderboardMetric,
  MatchList,
  MatchView,
  RoundView,
  SessionHistory,
  SessionState,
  StartSessionOptions,
  Theme,
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

  /** Сменить то, каким игрока видят другие: имя, аватарку или и то и другое. */
  updateProfile: (changes: {
    display_name?: string;
    avatar_shape?: number;
    avatar_color?: number;
  }) => request<UserProfile>("/api/auth/me", { method: "PATCH", body: changes }),

  /** Запомнить оформление. Отдельно от имени и аватарки: у той свой лимит. */
  setTheme: (theme: Theme) =>
    request<UserProfile>("/api/auth/me/theme", { method: "PUT", body: { theme } }),

  /** Удалить учётную запись со всеми данными. Пароль подтверждает владельца. */
  deleteAccount: (password: string) =>
    request<void>("/api/auth/me/delete", { method: "POST", body: { password } }),
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

  /** Взять подсказку: сервер раскроет место и уменьшит максимум раунда. */
  hint: (roundId: number) =>
    request<RoundView>(`/api/rounds/${String(roundId)}/hint`, { method: "POST" }),

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

export const friends = {
  list: () => request<FriendList>("/api/friends"),

  /** Позвать в друзья по коду игрока. */
  invite: (code: string) => request<Friend>("/api/friends", { method: "POST", body: { code } }),

  accept: (id: number) => request<Friend>(`/api/friends/${String(id)}/accept`, { method: "POST" }),

  /** Отклонить заявку, отозвать свою или расстаться — это одно действие. */
  remove: (id: number) => request<void>(`/api/friends/${String(id)}`, { method: "DELETE" }),
};

export const duels = {
  /** Условия дуэли. Не меняются, поэтому запрашиваются один раз. */
  format: () => request<DuelFormat>("/api/duels/format"),

  /** Сколько человек ищет соперника. Ничего не меняет. */
  searching: () => request<DuelSearch>("/api/duels/searching"),

  start: () => request<DuelSearch>("/api/duels/queue", { method: "POST" }),

  /** Продлить поиск и узнать, нашлась ли пара. */
  poll: () => request<DuelSearch>("/api/duels/queue/poll", { method: "POST" }),

  stop: () => request<void>("/api/duels/queue", { method: "DELETE" }),
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
  /** filters — строка вида "difficulty=hardcore&country_group=russia". */
  top: (metric: LeaderboardMetric, limit = 20, filters = "") =>
    request<Leaderboard>(
      `/api/leaderboard?metric=${metric}&limit=${String(limit)}${filters === "" ? "" : `&${filters}`}`,
    ),
};

export const zones = {
  /** query — строка вида "continent=europe&country_group=eu". */
  list: (query = "") => request<Zone[]>(`/api/zones${query === "" ? "" : `?${query}`}`),
};
