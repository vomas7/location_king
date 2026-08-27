/**
 * Кто отвечает за сервис.
 *
 * Значения приходят из public/config.js, чтобы их можно было поменять при
 * деплое, не пересобирая приложение. Пока они не заполнены, документы честно
 * говорят об этом вместо того, чтобы выдумывать контакт.
 */

const configured = window.__CONFIG__?.operator ?? {};

export const OPERATOR_NAME = (configured.name ?? "").trim();
export const OPERATOR_EMAIL = (configured.email ?? "").trim();

/** Как называть оператора в тексте документа. */
export function operatorName(): string {
  return OPERATOR_NAME === "" ? "оператор сервиса (реквизиты не указаны)" : OPERATOR_NAME;
}

/** Куда писать по вопросам о данных. */
export function operatorContact(): string {
  return OPERATOR_EMAIL === ""
    ? "Адрес для обращений не указан в конфигурации сервиса."
    : OPERATOR_EMAIL;
}
