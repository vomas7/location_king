/**
 * Условия партии: что игрок выбрал в меню и как это пересказать.
 *
 * Списки лежат здесь значениями, а подписи к ним — в словаре: значения
 * понимает сервер, а подписи зависят от языка. Списки нужны в двух местах:
 * настройками одиночной партии собирается и комната, и подпись под кнопкой
 * «Создать комнату» должна называть те же условия теми же словами.
 */

import type { StartSessionOptions } from "~/api/types";
import type { Formats } from "~/domain/format";
import type { PlaceKey } from "~/domain/place";
import { placeFilter } from "~/domain/place";
import type { Dictionary } from "~/i18n/dictionary";

/** Уровень: он же значение difficulty на сервере. */
export type LevelKey = "easy" | "normal" | "hard" | "hardcore";

/** Чем отвечать: точкой на карте, страной или выбором из шести. */
export type AnswerModeKey = "point" | "country" | "choice";

export interface GameSetup {
  rounds: number;
  level: LevelKey;
  place: PlaceKey;
  timeLimit: number | null;
  answerMode: AnswerModeKey;
}

export interface Choice<T> {
  value: T;
  label: string;
}

/**
 * Чем отвечать — и это главный выбор в игре, а не строчка настроек.
 *
 * Точкой — игрок ставит её на карте, очки за расстояние. Страной — на карте
 * подсвечены границы, он нажимает на страну. Выбором — карты нет вовсе, под
 * снимком шесть названий: так проще всего начать тому, кто по карте пока не
 * ориентируется.
 *
 * Порядок от простого к сложному: с ним список читается как лестница, по
 * которой поднимаются, а не как три равных варианта.
 */
export const ANSWER_MODES: AnswerModeKey[] = ["choice", "country", "point"];

export const ROUNDS: number[] = [3, 5, 10];

/**
 * Уровень — это выбор содержания, а не множитель очков. Подсказка объясняет,
 * что именно достанется: без неё «хардкор» звучит как «то же самое, но
 * обидно».
 *
 * Уровни не вложены друг в друга: выбрав «средне», Манхэттен не получишь.
 * Каждое место в каталоге размечено ровно одним уровнем.
 *
 * Ширину кадра уровень задаёт сам, на сервере: она не усиливает сложность, а
 * выравнивает её — чем меньше в кадре рукотворных ориентиров, тем больше
 * нужно контекста.
 */
export const LEVELS: LevelKey[] = ["easy", "normal", "hard", "hardcore"];

/** Сколько времени дают на раунд. Пусто — без ограничения. */
export const TIME_LIMIT_VALUES: (number | null)[] = [null, 120, 60, 30];

/**
 * Откуда берутся зоны. Список фиксирован: он должен совпадать с тем, что
 * понимает сервер, и не зависеть от того, какие зоны сейчас загружены.
 *
 * Страны и части света в одном переключателе намеренно: на сервере это разные
 * фильтры, но игроку нужно выбрать одно место, а не пересечение двух условий.
 * Евросоюз не совпадает с Европой — в неё входят ещё Британия, Норвегия,
 * Швейцария и Исландия.
 *
 * Рядом со значением — имя подписи в словаре: сами подписи переводятся, а
 * ключ вроде `continent:north_america` — нет.
 */
type PlaceName = keyof Dictionary["setup"]["places"];

export const PLACES: { value: PlaceKey; name: PlaceName }[] = [
  { value: null, name: "world" },
  { value: "country:russia", name: "russia" },
  { value: "country:usa", name: "usa" },
  { value: "country:eu", name: "eu" },
  { value: "continent:europe", name: "europe" },
  { value: "continent:asia", name: "asia" },
  { value: "continent:africa", name: "africa" },
  { value: "continent:north_america", name: "northAmerica" },
  { value: "continent:south_america", name: "southAmerica" },
  { value: "continent:oceania", name: "oceania" },
];

export const PLACE_VALUES: PlaceKey[] = PLACES.map((place) => place.value);

/** Переключатель «чем отвечать» на выбранном языке. */
export function answerModeChoices(text: Dictionary): (Choice<AnswerModeKey> & { hint: string })[] {
  return ANSWER_MODES.map((value) => ({ value, ...text.setup.answerModes[value] }));
}

export function levelChoices(text: Dictionary): (Choice<LevelKey> & { hint: string })[] {
  return LEVELS.map((value) => ({ value, ...text.setup.levels[value] }));
}

export function placeChoices(text: Dictionary): Choice<PlaceKey>[] {
  return PLACES.map(({ value, name }) => ({ value, label: text.setup.places[name] }));
}

/** Число раундов подписывает само себя. */
export function roundChoices(): Choice<number>[] {
  return ROUNDS.map((value) => ({ value, label: String(value) }));
}

/**
 * Время на раунд списком для переключателя. Подписи собираются по запросу, а
 * не лежат готовыми: «2 мин» и «2 min» — это уже язык.
 */
export function timeLimits(formats: Formats): Choice<number | null>[] {
  return TIME_LIMIT_VALUES.map((value) => ({ value, label: formats.timeLimit(value) }));
}

/** Настройки по умолчанию для того, кто уже играл: свои он выставит сам. */
export const DEFAULT_SETUP: GameSetup = {
  rounds: 5,
  level: "normal",
  place: null,
  timeLimit: null,
  answerMode: "point",
};

/** Подсказка под выбранным уровнем: что именно достанется на этом уровне. */
export function levelHint(text: Dictionary, level: LevelKey): string {
  return text.setup.levels[level].hint;
}

/** Подсказка под выбором ответа: за что дадут очки. */
export function answerModeHint(text: Dictionary, mode: AnswerModeKey): string {
  return text.setup.answerModes[mode].hint;
}

/**
 * Условия одной строкой — чтобы их было видно, не разворачивая настройки.
 *
 * Порядок тот же, что у переключателей: строка и панель настроек читаются
 * как одно и то же, только одна свёрнута.
 */
export function describeSetup(setup: GameSetup, text: Dictionary, formats: Formats): string {
  const place = PLACES.find((item) => item.value === setup.place)?.name ?? "world";

  return [
    text.setup.describeRounds(setup.rounds),
    text.setup.levels[setup.level].label,
    text.setup.places[place],
    formats.timeLimit(setup.timeLimit).toLowerCase(),
    // Ответ точкой — обычный ход игры, называть его каждый раз незачем.
    // А вот про страны игрок должен знать до того, как нажал «Начать»
    ...(setup.answerMode === "country" ? [text.setup.describeCountry] : []),
    ...(setup.answerMode === "choice" ? [text.setup.describeChoice] : []),
  ].join(" · ");
}

/**
 * Условия в том виде, в каком их принимает сервер.
 *
 * `category` — слой каталога: обычные места или достопримечательности. У
 * достопримечательностей уровень и место не спрашивают, поэтому в запрос они
 * и не уходят: их два десятка, и пересечение с «хардкором» или «Океанией»
 * оставило бы игрока без единой зоны.
 */
export function toOptions(setup: GameSetup, category: string | null = null): StartSessionOptions {
  const landmarks = category !== null;

  return {
    rounds_total: setup.rounds,
    category,
    difficulty: setup.level,
    ...(landmarks ? { continent: null, country_group: null } : placeFilter(setup.place)),
    answer_mode: setup.answerMode,
    time_limit_seconds: setup.timeLimit,
  };
}
