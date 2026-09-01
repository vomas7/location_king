/**
 * Оформление интерфейса.
 *
 * Проверяется не палитра, а то, что тема доезжает до разметки: в атрибуте
 * должно оказаться разрешённое значение, потому что светлая палитра описана
 * в токенах ровно один раз, под `[data-theme="light"]`.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  applyTheme,
  isTheme,
  rememberTheme,
  storedTheme,
  THEME_STORAGE_KEY,
  THEMES,
} from "~/domain/theme";

/** Слушатели системной настройки, чтобы её можно было переключить в тесте. */
let listeners: (() => void)[] = [];
let systemIsLight = false;

function stubMatchMedia() {
  vi.stubGlobal("matchMedia", (query: string) => ({
    media: query,
    get matches() {
      return systemIsLight;
    },
    addEventListener: (_: string, handler: () => void) => {
      listeners.push(handler);
    },
    removeEventListener: (_: string, handler: () => void) => {
      listeners = listeners.filter((item) => item !== handler);
    },
  }));
}

beforeEach(() => {
  listeners = [];
  systemIsLight = false;
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  stubMatchMedia();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("выбор темы", () => {
  it("знает ровно три варианта", () => {
    expect(THEMES).toEqual(["dark", "light", "system"]);
  });

  it("отличает тему от чего угодно другого", () => {
    expect(isTheme("light")).toBe(true);
    expect(isTheme("неоновая")).toBe(false);
    expect(isTheme(null)).toBe(false);
  });
});

describe("копия в браузере", () => {
  it("без записи считается системной", () => {
    expect(storedTheme()).toBe("system");
  });

  it("испорченное значение не притворяется темой", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "неоновая");

    expect(storedTheme()).toBe("system");
  });

  it("запомненное читается обратно", () => {
    rememberTheme("light");

    expect(storedTheme()).toBe("light");
  });
});

describe("применение темы", () => {
  it("ставит выбранную тему в разметку", () => {
    applyTheme("light");

    expect(document.documentElement.dataset["theme"]).toBe("light");
  });

  it("системную разрешает в конкретную", () => {
    systemIsLight = true;
    applyTheme("system");

    expect(document.documentElement.dataset["theme"]).toBe("light");
  });

  it("следит за системной настройкой, пока выбрана она", () => {
    applyTheme("system");
    expect(document.documentElement.dataset["theme"]).toBe("dark");

    systemIsLight = true;
    for (const listener of listeners) listener();

    expect(document.documentElement.dataset["theme"]).toBe("light");
  });

  it("перестаёт следить, когда за темой больше не смотрят", () => {
    const stop = applyTheme("system");
    stop();

    expect(listeners).toHaveLength(0);
  });

  it("на выбранной теме за системной не следит вовсе", () => {
    applyTheme("dark");

    expect(listeners).toHaveLength(0);
  });
});
