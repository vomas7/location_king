/**
 * Выбор игрока в меню, переживающий партию.
 *
 * Меню исчезает с экрана на время игры и собирается заново, когда партия
 * закончилась. Своего места, где этот выбор мог бы пережить партию, у него
 * нет, поэтому он лежит в браузере — там же он переживёт и перезагрузку
 * страницы.
 */

import { useCallback, useEffect, useState } from "react";

import type { MenuState } from "~/domain/menu";
import { defaultMenu, MENU_STORAGE_KEY, parseMenu } from "~/domain/menu";
import type { GameSetup } from "~/domain/setup";

export interface MenuController {
  menu: MenuState;
  change: (patch: Partial<MenuState>) => void;
}

/**
 * fresh — условия для того, кто ещё ничего не выбирал: у новичка они свои.
 * Сохранённый выбор сильнее: если игрок что-то трогал, это его выбор.
 */
export function useMenuState(fresh: GameSetup): MenuController {
  const [menu, setMenu] = useState<MenuState>(() => {
    const fallback = defaultMenu(fresh);
    try {
      return parseMenu(localStorage.getItem(MENU_STORAGE_KEY), fallback);
    } catch {
      // Приватный режим: меню каждый раз начинается с чистого листа
      return fallback;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(MENU_STORAGE_KEY, JSON.stringify(menu));
    } catch {
      // Записать не вышло — выбор доживёт до конца этого посещения
    }
  }, [menu]);

  const change = useCallback((patch: Partial<MenuState>) => {
    setMenu((current) => ({ ...current, ...patch }));
  }, []);

  return { menu, change };
}
