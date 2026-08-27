/// <reference types="vite/client" />

/** Конфигурация окружения из public/config.js. */
interface RuntimeConfig {
  apiBase?: string;
  /** Кто отвечает за сервис. Подставляется при деплое и попадает в документы. */
  operator?: {
    name?: string;
    email?: string;
  };
}

interface Window {
  __CONFIG__?: RuntimeConfig;
}
