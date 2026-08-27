/**
 * Удержание фокуса внутри модального окна.
 *
 * Без этого Tab уводит в интерфейс под оверлеем: с клавиатуры пользователь
 * начинает нажимать кнопки, которых не видит.
 */

import { useEffect, type RefObject } from "react";

const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

export function useFocusTrap(container: RefObject<HTMLElement>): void {
  useEffect(() => {
    const element = container.current;
    if (element === null) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;

      const items = [...element.querySelectorAll<HTMLElement>(FOCUSABLE)];
      const first = items[0];
      const last = items[items.length - 1];

      if (first === undefined || last === undefined) return;

      const active = document.activeElement;

      if (event.shiftKey && (active === first || !element.contains(active))) {
        event.preventDefault();
        last.focus();
        return;
      }

      if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };

    element.addEventListener("keydown", onKeyDown);
    return () => {
      element.removeEventListener("keydown", onKeyDown);
    };
  }, [container]);
}
