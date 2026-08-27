/**
 * Типы ответов API.
 *
 * Повторяют схемы бэкенда один в один. Важное свойство контракта видно прямо
 * здесь: у активного раунда (RoundView) нет ни одного поля с координатами —
 * они появляются только в RoundResult, то есть после принятой догадки.
 */

export interface UserProfile {
  id: number;
  username: string;
  display_name: string | null;
  email: string;
  total_score: number;
  games_played: number;
  total_rounds: number;
  best_score: number;
  average_score: number | null;
  average_distance: number | null;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  user: UserProfile;
  tokens: TokenPair;
}

export interface Zone {
  id: number;
  name: string;
  description: string | null;
  difficulty: number;
  difficulty_name: string;
  category: string;
  category_name: string;
  country: string | null;
  region: string | null;
  tags: string[];
}

/** Активный раунд: снимок доступен только через tiles_url. */
export interface RoundView {
  id: number;
  index: number;
  status: string;
  view_extent_km: string;
  max_zoom: number;
  tiles_url: string;
  attribution: string;
  created_at: string;
}

/** Завершённый раунд: здесь цель уже раскрыта. */
export interface RoundResult {
  id: number;
  index: number;
  status: string;
  view_extent_km: string;
  target: [number, number];
  guess: [number, number] | null;
  distance_km: string | null;
  score: number;
  max_score: number;
  accuracy: string | null;
  zone: Zone;
  guessed_at: string | null;
}

export interface SessionView {
  id: string;
  status: string;
  /** Заполнено, если партия относится к челленджу этого дня. */
  challenge_day: string | null;
  rounds_total: number;
  rounds_done: number;
  total_score: number;
  average_score: number | null;
  started_at: string;
  finished_at: string | null;
}

export interface SessionState {
  session: SessionView;
  current_round: RoundView | null;
  results: RoundResult[];
}

export interface GuessResponse {
  result: RoundResult;
  session: SessionView;
  next_round: RoundView | null;
  is_session_finished: boolean;
}

export interface SessionSummary {
  id: string;
  status: string;
  challenge_day: string | null;
  rounds_total: number;
  rounds_done: number;
  total_score: number;
  started_at: string;
  finished_at: string | null;
}

export interface SessionHistory {
  sessions: SessionSummary[];
  total: number;
}

export type LeaderboardMetric = "best" | "total" | "accuracy";

export interface LeaderboardEntry {
  rank: number;
  user_id: number;
  display_name: string;
  games_played: number;
  total_rounds: number;
  best_score: number;
  total_score: number;
  average_distance: number | null;
}

export interface Leaderboard {
  metric: LeaderboardMetric;
  entries: LeaderboardEntry[];
  me: LeaderboardEntry | null;
}

/** Параметры новой партии. */
export interface StartSessionOptions {
  rounds_total: number;
  view_extent_km: number;
  difficulty: number | null;
}

export interface DailyResult {
  rank: number;
  display_name: string;
  total_score: number;
  finished_at: string | null;
}

export interface DailyChallenge {
  day: string;
  rounds_total: number;
  view_extent_km: number;
  /** Партия игрока по этому челленджу, если он его уже начинал. */
  my_session: SessionSummary | null;
  finished_players: number;
  results: DailyResult[];
}
