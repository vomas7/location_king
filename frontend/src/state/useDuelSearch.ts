/**
 * Поиск соперника.
 *
 * Живого соединения нет: клиент опрашивает сервер, и тот же запрос продлевает
 * запись в очереди. Перестал опрашивать — выпал из неё сам, поэтому вкладку
 * можно просто закрыть.
 *
 * Пока игрок не ищет, счётчик всё равно опрашивается, но втрое реже: решать,
 * стоит ли вставать в очередь, он должен до того, как встал.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "~/api/client";
import { duels, matches } from "~/api/endpoints";
import type { SessionState } from "~/api/types";

export type DuelPhase =
  | "idle" // не ищем
  | "searching" // стоим в очереди
  | "joining"; // пара нашлась, входим в дуэль

/** Как часто опрашивать сервер, пока ищем и пока не ищем. */
const SEARCH_POLL_MS = 3000;
const IDLE_POLL_MS = 15000;

export interface DuelSearchController {
  phase: DuelPhase;
  /** Сколько человек ищет соперника прямо сейчас. */
  searching: number;
  error: string | null;
  start: () => void;
  stop: () => void;
}

function describe(error: unknown): string {
  return error instanceof ApiError ? error.detail : "Сервер недоступен. Попробуй ещё раз";
}

export function useDuelSearch(onFound: (session: SessionState) => void): DuelSearchController {
  const [phase, setPhase] = useState<DuelPhase>("idle");
  const [searching, setSearching] = useState(0);
  const [found, setFound] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onFoundRef = useRef(onFound);
  onFoundRef.current = onFound;

  // Ищем ли прямо сейчас — для уборки при размонтировании. Через состояние
  // этого не узнать: эффект уборки видит то, что было на момент подписки
  const searchingRef = useRef(false);
  searchingRef.current = phase === "searching";

  // ── Счётчик у кнопки ────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== "idle") return;

    let cancelled = false;

    const tick = async () => {
      try {
        const state = await duels.searching();
        if (!cancelled) setSearching(state.searching);
      } catch {
        // Счётчик — подпись у кнопки, а не условие игры: без него кнопка
        // работает, и разговаривать с игроком об этом незачем
      }
    };

    void tick();
    const timer = window.setInterval(() => void tick(), IDLE_POLL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [phase]);

  // ── Сам поиск ───────────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== "searching") return;

    let cancelled = false;

    const tick = async () => {
      try {
        const state = await duels.poll();
        if (cancelled) return;

        setSearching(state.searching);
        if (state.code !== null) setFound(state.code);
      } catch (error) {
        if (cancelled) return;
        setError(describe(error));
        setPhase("idle");
      }
    };

    const timer = window.setInterval(() => void tick(), SEARCH_POLL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [phase]);

  // ── Вход в найденную дуэль ──────────────────────────────────────────
  // Отдельно от поиска: вход меняет фазу, а значит, обрывает эффект поиска
  // вместе со своим же продолжением, если делать его там
  useEffect(() => {
    if (found === null) return;

    let cancelled = false;
    setPhase("joining");

    void (async () => {
      try {
        const session = await matches.join(found);
        if (!cancelled) onFoundRef.current(session);
      } catch (error) {
        if (!cancelled) setError(describe(error));
      } finally {
        if (!cancelled) {
          setFound(null);
          setPhase("idle");
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [found]);

  // ── Уборка при уходе со страницы ────────────────────────────────────
  useEffect(
    () => () => {
      if (!searchingRef.current) return;

      void duels.stop().catch(() => {
        // Запись в очереди протухнет сама через несколько секунд — этот
        // запрос только ускоряет неизбежное
      });
    },
    [],
  );

  const start = useCallback(() => {
    setError(null);

    void (async () => {
      try {
        const state = await duels.start();
        setSearching(state.searching);
        setPhase("searching");
      } catch (error) {
        setError(describe(error));
      }
    })();
  }, []);

  const stop = useCallback(() => {
    setPhase("idle");

    void duels.stop().catch(() => {
      // То же самое: очередь забудет игрока и без этого запроса
    });
  }, []);

  return { phase, searching, error, start, stop };
}
