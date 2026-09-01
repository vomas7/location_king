/**
 * Типы ответов API.
 *
 * Повторяют схемы бэкенда один в один. Важное свойство контракта видно прямо
 * здесь: у активного раунда (RoundView) нет ни одного поля с координатами —
 * они появляются только в RoundResult, то есть после принятой догадки.
 */

/** Аватарка: форма узора и цвет. Картинку по ним рисует клиент. */
/**
 * Ответ игрока на раунд: точка на карте или страна.
 *
 * Чем именно отвечают, решает раунд, а не игрок: в обычном ставят точку, в
 * раунде про страны выбирают страну на карте. Название страны нужно только
 * чтобы показать его в панели — серверу уходит код.
 */
export type Answer =
  | { kind: "point"; longitude: number; latitude: number }
  | { kind: "country"; code: string; name: string };

/** О чём написал игрок. Те же значения понимает сервер. */
export type FeedbackKind = "impression" | "problem";

/** Записанный отзыв: возвращается автору, чтобы было видно, что дошло. */
export interface FeedbackView {
  id: number;
  kind: FeedbackKind;
  message: string;
  created_at: string;
}

/** Оформление интерфейса. Те же значения понимает сервер. */
export type Theme = "dark" | "light" | "system";

export interface AvatarView {
  /** Форма узора и его цвет. Узор есть у каждого, рисует его клиент. */
  shape: number;
  color: number;
  /** Адрес загруженной картинки. Пусто — значит, игрок ничего не загружал. */
  image_url: string | null;
}

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
  /** Рейтинг дуэлей. У того, кто ещё не дуэлился, он стартовый. */
  rating: number;
  duels_played: number;
  avatar: AvatarView;
  /** Оформление интерфейса. Приезжает с профилем: выбор хранится у игрока. */
  theme: Theme;
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
  category: string;
  category_name: string;
  continent: string | null;
  continent_name: string;
  country: string | null;
  region: string | null;
  tags: string[];
  /** Сколько раз зона сыграна всеми игроками. */
  total_rounds: number;
  /** Средний промах по этим раундам в километрах. */
  average_distance: number | null;
}

/** Раскрытая подсказка: подпись поля и его значение. Координат в ней нет. */
export interface HintView {
  label: string;
  value: string;
}

/** Активный раунд: снимок доступен только через tiles_url. */
/** Вариант ответа в режиме выбора. */
export interface CountryChoice {
  code: string;
  name: string;
}

export interface RoundView {
  id: number;
  index: number;
  status: string;
  view_extent_km: string;
  max_zoom: number;
  tiles_url: string;
  attribution: string;
  created_at: string;
  /** Чем отвечать на этот раунд: point — точкой, country — страной. */
  answer_mode: string;
  /** Варианты для режима выбора. Пусто в остальных: там отвечают по карте. */
  choices: CountryChoice[];
  /** Сколько очков ещё можно взять за раунд. Подсказка это число уменьшает. */
  max_score: number;
  /** Заполнено, если игрок взял подсказку. */
  hint: HintView | null;
  /** Во сколько очков обойдётся подсказка. 0 — брать нечего или уже взята. */
  hint_cost: number;
  /** До какого момента принимается ответ. null — время не ограничено. */
  deadline_at: string | null;
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
  /**
   * Страна цели и страна, куда попал игрок. Заполнены только в режиме стран:
   * в обычном раунде вопрос был не про страну. Пустая страна догадки
   * означает, что точка легла мимо суши.
   */
  country: string | null;
  guess_country: string | null;
  answer_seconds: string | null;
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
  time_limit_seconds: number | null;
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
  avatar: AvatarView;
  games_played: number;
  total_rounds: number;
  best_score: number;
  total_score: number;
  average_distance: number | null;
}

export interface Leaderboard {
  metric: LeaderboardMetric;
  /** Условия, по которым отобраны партии. null — считались все. */
  difficulty: string | null;
  continent: string | null;
  country_group: string | null;
  /** Зачёт сужен до друзей игрока и его самого. */
  among_friends: boolean;
  entries: LeaderboardEntry[];
  me: LeaderboardEntry | null;
}

/**
 * Параметры новой партии.
 *
 * Ширины кадра здесь нет: её задаёт уровень, и считает это сервер. Игрок её
 * не выбирает — два независимых регулятора сложности сводились в
 * бессмысленную пару.
 */
export interface StartSessionOptions {
  rounds_total: number;
  /** Часть света, из которой берутся зоны. null — со всего мира. */
  continent: string | null;
  /** Страна или объединение стран. null — не ограничивать. */
  country_group: string | null;
  /** Уровень: easy, normal, hard или hardcore. Он же выбирает, что покажут. */
  difficulty: string;
  /** Чем отвечать: point — точкой на карте, country — страной. */
  answer_mode: string;
  /** Сколько секунд даётся на раунд. null — без ограничения. */
  time_limit_seconds: number | null;
}

export interface DailyResult {
  rank: number;
  display_name: string;
  avatar: AvatarView;
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
  /** Сколько дней подряд игрок доходит до конца челленджа. */
  current_streak: number;
  /** Самая длинная его серия за всё время. */
  best_streak: number;
  results: DailyResult[];
}

/**
 * Связь с другим игроком: подтверждённая дружба или заявка.
 *
 * id — идентификатор связи, а не игрока: чужих идентификаторов сервер не
 * отдаёт. По нему заявку принимают и убирают, больше он ни для чего не нужен.
 */
export interface Friend {
  id: number;
  display_name: string;
  avatar: AvatarView;
  rating: number;
  accepted: boolean;
  /** Заявка пришла ко мне и ждёт ответа. */
  incoming: boolean;
  created_at: string;
}

export interface FriendList {
  /** Код игрока: его показывают тем, кого хотят добавить. */
  my_code: string;
  friends: Friend[];
}

/** Строка таблицы комнаты. Чужих идентификаторов сервер не отдаёт. */
export interface MatchStanding {
  rank: number;
  display_name: string;
  avatar: AvatarView;
  total_score: number;
  rounds_done: number;
  is_finished: boolean;
  /** Своя строка — её и подсвечиваем. */
  is_you: boolean;
  finished_at: string | null;
}

export interface MatchView {
  code: string;
  status: string;
  host_name: string;
  is_host: boolean;
  rounds_total: number;
  time_limit_seconds: number | null;
  players: number;
  created_at: string;
  /** Партия игрока в этой комнате, если он уже входил. */
  my_session: SessionSummary | null;
  standings: MatchStanding[];
}

export interface MatchSummary {
  code: string;
  status: string;
  rounds_total: number;
  players: number;
  created_at: string;
}

export interface MatchList {
  matches: MatchSummary[];
}

/** Состояние поиска соперника. */
export interface DuelSearch {
  /** Сколько человек ищет прямо сейчас. */
  searching: number;
  /** Код дуэли, если пара нашлась. Дальше в неё входят как в комнату. */
  code: string | null;
}

/** Условия дуэли: одни и те же для всех, их решает сервер. */
export interface DuelFormat {
  rounds_total: number;
  view_extent_km: number;
  difficulty: string;
  time_limit_seconds: number;
}
