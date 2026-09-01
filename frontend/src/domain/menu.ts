/**
 * Состояние меню: условия партии, открытый режим и открытый раздел.
 *
 * Меню размонтируется на время партии, поэтому обычный useState терял бы всё
 * это после каждой игры: выставленный «хардкор по Азии» приходилось бы
 * набирать заново, а после партии в комнате игрок возвращался бы на вкладку
 * одиночной. Поэтому выбор лежит в браузере — это не настройка учётной
 * записи, как тема, а место, на котором игрок остановился.
 *
 * Всё прочитанное сверяется со списками вариантов: в хранилище может лежать
 * что угодно — старая версия, ручная правка, — а «Азия» из позапрошлого
 * релиза означала бы партию, для которой сервер не находит ни одной зоны.
 */

import type { GameSetup } from "~/domain/setup";
import { ANSWER_MODES, LEVELS, PLACE_VALUES, ROUNDS, TIME_LIMIT_VALUES } from "~/domain/setup";

/** Ключ в localStorage. Он назван в документе про хранилище, и тест это сверяет. */
export const MENU_STORAGE_KEY = "location-king:menu";

/** Чем играть. */
export type ModeKey = "solo" | "landmarks" | "daily" | "duel" | "room";

/** Что смотреть: разделы, в которые не играют. */
export type SectionKey = "profile" | "friends" | "board" | "history";

const MODE_KEYS: ModeKey[] = ["solo", "landmarks", "daily", "duel", "room"];

/** Порядок разделов. Подписи к ним — в словаре: они переводятся */
export const SECTIONS: SectionKey[] = ["profile", "friends", "board", "history"];

export interface MenuState {
  setup: GameSetup;
  mode: ModeKey;
  section: SectionKey;
}

/** Меню, каким его видит игрок, который ещё ничего не выбирал. */
export function defaultMenu(setup: GameSetup): MenuState {
  return { setup, mode: "solo", section: "profile" };
}

/**
 * Разобрать сохранённое меню. Всё, что не сходится со списками вариантов,
 * заменяется значением из fallback — разбор не падает и не отдаёт мусор.
 */
export function parseMenu(raw: string | null, fallback: MenuState): MenuState {
  if (raw === null) return fallback;

  let stored: unknown;
  try {
    stored = JSON.parse(raw);
  } catch {
    // В хранилище лежит не JSON: начинаем с чистого меню
    return fallback;
  }

  if (typeof stored !== "object" || stored === null) return fallback;
  const fields = stored as Record<string, unknown>;

  return {
    setup: parseSetup(fields.setup, fallback.setup),
    mode: MODE_KEYS.find((key) => key === fields.mode) ?? fallback.mode,
    section: oneOf(SECTIONS, fields.section, fallback.section),
  };
}

function parseSetup(stored: unknown, fallback: GameSetup): GameSetup {
  if (typeof stored !== "object" || stored === null) return fallback;
  const fields = stored as Record<string, unknown>;

  return {
    rounds: oneOf(ROUNDS, fields.rounds, fallback.rounds),
    level: oneOf(LEVELS, fields.level, fallback.level),
    place: oneOf(PLACE_VALUES, fields.place, fallback.place),
    timeLimit: oneOf(TIME_LIMIT_VALUES, fields.timeLimit, fallback.timeLimit),
    answerMode: oneOf(ANSWER_MODES, fields.answerMode, fallback.answerMode),
  };
}

/** Значение из списка вариантов — или запасное, если такого варианта нет. */
function oneOf<T>(values: T[], stored: unknown, fallback: T): T {
  return values.some((value) => value === stored) ? (stored as T) : fallback;
}
