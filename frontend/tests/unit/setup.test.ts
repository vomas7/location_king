/** Условия партии: строка под кнопкой и параметры запроса. */

import { describe, expect, it } from "vitest";

import { formats } from "~/domain/format";
import { DEFAULT_SETUP, describeSetup, levelHint, toOptions } from "~/domain/setup";

const ru = formats("ru");

describe("describeSetup", () => {
  it("называет все условия подряд", () => {
    // Ширины кадра здесь нет: её задаёт уровень, и выбирать её игрок не может
    expect(describeSetup(DEFAULT_SETUP, ru)).toBe("5 раундов · Средне · Весь мир · без лимита");
  });

  it("склоняет раунды", () => {
    expect(describeSetup({ ...DEFAULT_SETUP, rounds: 3 }, ru)).toContain("3 раунда");
    expect(describeSetup({ ...DEFAULT_SETUP, rounds: 10 }, ru)).toContain("10 раундов");
  });

  it("называет выбранное место, а не ключ фильтра", () => {
    expect(describeSetup({ ...DEFAULT_SETUP, place: "continent:oceania" }, ru)).toContain(
      "Океания",
    );
    expect(describeSetup({ ...DEFAULT_SETUP, place: "country:eu" }, ru)).toContain("Евросоюз");
  });

  it("называет таймер", () => {
    expect(describeSetup({ ...DEFAULT_SETUP, timeLimit: 30 }, ru)).toContain("30 сек");
  });

  it("предупреждает про ответ страной и молчит про обычный ответ", () => {
    expect(describeSetup({ ...DEFAULT_SETUP, answerMode: "country" }, ru)).toContain(
      "ответ страной",
    );
    expect(describeSetup(DEFAULT_SETUP, ru)).not.toContain("ответ");
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
    expect(levelHint("hardcore")).toContain("Дикая природа");
  });

  it("молчит про уровень, которого нет в списке", () => {
    expect(levelHint("nightmare")).toBe("");
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
