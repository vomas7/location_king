/**
 * Условия партии: что игрок выбрал в меню и как это пересказать.
 *
 * Списки лежат здесь, а не в компоненте, потому что нужны в двух местах:
 * настройками одиночной партии собирается и комната, и подпись под кнопкой
 * «Создать комнату» должна называть те же условия теми же словами.
 */

import type { StartSessionOptions } from "~/api/types";
import { formatTimeLimit, plural } from "~/domain/format";
import type { PlaceKey } from "~/domain/place";
import { placeFilter } from "~/domain/place";

export interface GameSetup {
  rounds: number;
  extent: number;
  level: string;
  place: PlaceKey;
  timeLimit: number | null;
  /** Чем отвечать: point — точкой на карте, country — страной. */
  answerMode: string;
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
export const ANSWER_MODES: (Choice<string> & { hint: string })[] = [
  {
    value: "choice",
    label: "Из шести",
    hint: "Под снимком шесть стран, одна верная. Самый простой способ начать",
  },
  {
    value: "country",
    label: "Страной",
    hint: "Карта со странами: попал — максимум, мимо — по промаху",
  },
  { value: "point", label: "Точкой", hint: "Точка на карте мира, очки за близость к цели" },
];

export const ROUNDS: Choice<number>[] = [3, 5, 10].map((value) => ({
  value,
  label: String(value),
}));

/**
 * Уровень — это выбор содержания, а не множитель очков. Подсказка объясняет,
 * что именно достанется: без неё «хардкор» звучит как «то же самое, но
 * обидно».
 *
 * Уровни не вложены друг в друга: выбрав «средне», Манхэттен не получишь.
 * Каждое место в каталоге размечено ровно одним уровнем.
 */
export const LEVELS: (Choice<string> & { hint: string })[] = [
  { value: "easy", label: "Легко", hint: "Узнают по силуэту: Париж, Венеция, Манхэттен" },
  {
    value: "normal",
    label: "Средне",
    hint: "Крупные города знакомых стран: Гамбург, Казань, Сиэтл",
  },
  {
    value: "hard",
    label: "Сложно",
    hint: "Города, о которых знают мало, и обжитая местность без города",
  },
  { value: "hardcore", label: "Хардкор", hint: "Дикая природа: горы, пустыни, тайга, лёд" },
];

/**
 * Сколько земли попадает в кадр. Пять километров плотного города — это одна
 * текстура кварталов без ориентиров, поэтому лестница начинается там, где
 * в кадр уже попадает река, шоссе или берег.
 */
export const EXTENTS: Choice<number>[] = [5, 15, 40, 100].map((value) => ({
  value,
  label: `${String(value)} км`,
}));

export const TIME_LIMITS: Choice<number | null>[] = [null, 120, 60, 30].map((value) => ({
  value,
  label: formatTimeLimit(value),
}));

/**
 * Откуда берутся зоны. Список фиксирован: он должен совпадать с тем, что
 * понимает сервер, и не зависеть от того, какие зоны сейчас загружены.
 *
 * Страны и части света в одном переключателе намеренно: на сервере это разные
 * фильтры, но игроку нужно выбрать одно место, а не пересечение двух условий.
 * Евросоюз не совпадает с Европой — в неё входят ещё Британия, Норвегия,
 * Швейцария и Исландия.
 */
export const PLACES: Choice<PlaceKey>[] = [
  { value: null, label: "Весь мир" },
  { value: "country:russia", label: "Россия" },
  { value: "country:usa", label: "США" },
  { value: "country:eu", label: "Евросоюз" },
  { value: "continent:europe", label: "Европа" },
  { value: "continent:asia", label: "Азия" },
  { value: "continent:africa", label: "Африка" },
  { value: "continent:north_america", label: "Сев. Америка" },
  { value: "continent:south_america", label: "Юж. Америка" },
  { value: "continent:oceania", label: "Океания" },
];

/** Настройки по умолчанию для того, кто уже играл: свои он выставит сам. */
export const DEFAULT_SETUP: GameSetup = {
  rounds: 5,
  extent: 15,
  level: "normal",
  place: null,
  timeLimit: null,
  answerMode: "point",
};

function labelOf<T>(choices: Choice<T>[], value: T, fallback: string): string {
  return choices.find((choice) => choice.value === value)?.label ?? fallback;
}

/** Подсказка под выбранным уровнем: что именно достанется на этом уровне. */
export function levelHint(level: string): string {
  return LEVELS.find((choice) => choice.value === level)?.hint ?? "";
}

/** Подсказка под выбором ответа: за что дадут очки. */
export function answerModeHint(mode: string): string {
  return ANSWER_MODES.find((choice) => choice.value === mode)?.hint ?? "";
}

/**
 * Условия одной строкой — чтобы их было видно, не разворачивая настройки.
 *
 * Порядок тот же, что у переключателей: строка и панель настроек читаются
 * как одно и то же, только одна свёрнута.
 */
export function describeSetup(setup: GameSetup): string {
  return [
    `${String(setup.rounds)} ${plural(setup.rounds, "раунд", "раунда", "раундов")}`,
    labelOf(LEVELS, setup.level, setup.level),
    labelOf(EXTENTS, setup.extent, `${String(setup.extent)} км`),
    labelOf(PLACES, setup.place, "Весь мир"),
    labelOf(TIME_LIMITS, setup.timeLimit, formatTimeLimit(setup.timeLimit)).toLowerCase(),
    // Ответ точкой — обычный ход игры, называть его каждый раз незачем.
    // А вот про страны игрок должен знать до того, как нажал «Начать»
    ...(setup.answerMode === "country" ? ["ответ страной"] : []),
    ...(setup.answerMode === "choice" ? ["выбор из шести"] : []),
  ].join(" · ");
}

/** Условия в том виде, в каком их принимает сервер. */
export function toOptions(setup: GameSetup): StartSessionOptions {
  return {
    rounds_total: setup.rounds,
    view_extent_km: setup.extent,
    difficulty: setup.level,
    ...placeFilter(setup.place),
    answer_mode: setup.answerMode,
    time_limit_seconds: setup.timeLimit,
  };
}
