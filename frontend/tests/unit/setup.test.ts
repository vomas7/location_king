/** Условия партии: строка под кнопкой и параметры запроса. */

import { describe, expect, it } from "vitest";

import { formats } from "~/domain/format";
import { en } from "~/i18n/en";
import { ru as text } from "~/i18n/ru";
import { DEFAULT_SETUP, describeSetup, LEVELS, levelHint, toOptions } from "~/domain/setup";

const ru = formats("ru");

describe("describeSetup", () => {
  it("называет все условия подряд", () => {
    // Ширины кадра здесь нет: её задаёт уровень, и выбирать её игрок не может
    expect(describeSetup(DEFAULT_SETUP, text, ru)).toBe(
      "5 раундов · Средне · Весь мир · без лимита",
    );
  });

  it("склоняет раунды", () => {
    expect(describeSetup({ ...DEFAULT_SETUP, rounds: 3 }, text, ru)).toContain("3 раунда");
    expect(describeSetup({ ...DEFAULT_SETUP, rounds: 10 }, text, ru)).toContain("10 раундов");
  });

  it("называет выбранное место, а не ключ фильтра", () => {
    expect(describeSetup({ ...DEFAULT_SETUP, place: "continent:oceania" }, text, ru)).toContain(
      "Океания",
    );
    expect(describeSetup({ ...DEFAULT_SETUP, place: "country:eu" }, text, ru)).toContain(
      "Евросоюз",
    );
  });

  it("называет таймер", () => {
    expect(describeSetup({ ...DEFAULT_SETUP, timeLimit: 30 }, text, ru)).toContain("30 сек");
  });

  it("предупреждает про ответ страной и молчит про обычный ответ", () => {
    expect(describeSetup({ ...DEFAULT_SETUP, answerMode: "country" }, text, ru)).toContain(
      "ответ страной",
    );
    expect(describeSetup(DEFAULT_SETUP, text, ru)).not.toContain("ответ");
  });
});

describe("toOptions", () => {
  it("разбирает место в два фильтра сервера", () => {
    expect(toOptions({ ...DEFAULT_SETUP, place: "continent:europe" })).toEqual({
      rounds_total: 5,
      category: null,
      difficulty: "normal",
      continent: "europe",
      country_group: null,
      answer_mode: "point",
      time_limit_seconds: null,
    });
  });

  it("передаёт выбранный способ ответа", () => {
    expect(toOptions({ ...DEFAULT_SETUP, answerMode: "country" }).answer_mode).toBe("country");
  });

  it("весь мир не ограничивает ничем", () => {
    const options = toOptions(DEFAULT_SETUP);

    expect(options.continent).toBeNull();
    expect(options.country_group).toBeNull();
  });
});

describe("levelHint", () => {
  it("объясняет каждый уровень", () => {
    expect(levelHint(text, "hardcore")).toContain("Дикая природа");
  });

  it("подсказка есть у всех уровней и на обоих языках", () => {
    for (const level of LEVELS) {
      expect(levelHint(text, level).length).toBeGreaterThan(10);
      expect(levelHint(en, level).length).toBeGreaterThan(10);
    }
  });
});

describe("слой каталога", () => {
  it("обычная партия идёт по всему каталогу, кроме известных мест", () => {
    expect(toOptions(DEFAULT_SETUP).category).toBeNull();
  });

  it("у известных мест не спрашивают ни уровень, ни место", () => {
    // Их два десятка на весь мир: пересечение с «Океанией» или «хардкором»
    // оставило бы игрока без единой зоны
    const options = toOptions({ ...DEFAULT_SETUP, place: "continent:oceania" }, "landmark");

    expect(options.category).toBe("landmark");
    expect(options.continent).toBeNull();
    expect(options.country_group).toBeNull();
  });
});
