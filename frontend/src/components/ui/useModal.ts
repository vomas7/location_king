/**
 * Поведение модального окна: удержание фокуса и закрытие по Escape.
 *
 * Без ловушки Tab уводит в интерфейс под оверлеем: с клавиатуры человек
 * начинает нажимать кнопки, которых не видит.
 *
 * Escape закрывает всё, что вообще закрывается, — это первое, что пробует
 * каждый, кому окно больше не нужно. Раньше его понимал только диалог
 * правовых документов, а форма отзыва и удаление аккаунта на Escape не
 * отвечали: на телефоне такое окно закрывается кнопкой, а с клавиатуры —
 * ничем. Окно без onClose (разбор раунда) отменить нельзя, и Escape там
 * ничего не делает.
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

/**
 * open обязателен, и не для красоты. Окно появляется в разметке позже, чем
 * вызывается хук: пока оно закрыто, ref пуст, эффект выходит ни с чем — и
 * без этой зависимости больше не запускается никогда. Именно поэтому в форме
 * отзыва и в удалении аккаунта не работали ни Escape, ни ловушка фокуса.
 */
export function useModal(
  container: RefObject<HTMLElement>,
  open: boolean,
  onClose?: () => void,
): void {
  useEffect(() => {
    const element = container.current;
    if (!open || element === null) return;

    // Фокус переводится внутрь сразу: пока он снаружи, ни Escape, ни ловушка
    // Tab до окна не доходят — нажатия достаются кнопке, которая его открыла
    if (!element.contains(document.activeElement)) {
      element.querySelector<HTMLElement>(FOCUSABLE)?.focus();
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && onClose !== undefined) {
        onClose();
        return;
      }

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

    // Слушаем на документе, а не на самом окне: фокус может уйти на элемент
    // под оверлеем, и тогда Escape мимо окна ничего бы не закрывал
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [container, open, onClose]);
}
