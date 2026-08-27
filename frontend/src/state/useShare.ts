/**
 * Отдать текст наружу: системное окно «поделиться», иначе буфер обмена.
 *
 * Вынесено из кнопки, потому что делиться приходится и результатом партии, и
 * ссылкой на комнату, а поведение браузеров у этих случаев одно.
 */

import { useCallback, useEffect, useRef, useState } from "react";

export type ShareState = "idle" | "shared" | "copied" | "failed";

/** Через сколько подпись на кнопке возвращается к обычной. */
const RESET_MS = 3000;

export function useShare(): { state: ShareState; share: (text: string) => void } {
  const [state, setState] = useState<ShareState>("idle");
  const timer = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (timer.current !== null) window.clearTimeout(timer.current);
    },
    [],
  );

  const share = useCallback((text: string) => {
    void (async () => {
      // Системное окно есть на телефонах и в части десктопных браузеров
      if (typeof navigator.share === "function") {
        try {
          await navigator.share({ text });
          setState("shared");
          return;
        } catch {
          // Игрок закрыл окно или браузер отказал — пробуем буфер
        }
      }

      try {
        await navigator.clipboard.writeText(text);
        setState("copied");
      } catch {
        setState("failed");
      }

      if (timer.current !== null) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => {
        setState("idle");
      }, RESET_MS);
    })();
  }, []);

  return { state, share };
}
