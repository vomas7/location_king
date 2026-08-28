/**
 * Челлендж дня.
 *
 * Его состояние нужно в двух местах сразу: на плитке режима — серией дней и
 * отметкой «сыграно», и в самой панели — таблицей дня. Запрос при этом должен
 * быть один, поэтому он живёт здесь, а не внутри панели.
 */

import { useEffect, useState } from "react";

import { challenge } from "~/api/endpoints";
import type { DailyChallenge } from "~/api/types";

/** Пусто, пока ответ не пришёл или если он не пришёл вовсе. */
export function useDailyChallenge(refreshKey: number): DailyChallenge | null {
  const [data, setData] = useState<DailyChallenge | null>(null);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      try {
        const loaded = await challenge.today();
        if (!cancelled) setData(loaded);
      } catch {
        // Челлендж — один из режимов, а не условие работы меню: не приехал —
        // плитка скажет об этом сама, остальное меню работает
        if (!cancelled) setData(null);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return data;
}
