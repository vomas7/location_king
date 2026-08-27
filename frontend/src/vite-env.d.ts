/// <reference types="vite/client" />

/** Конфигурация окружения из public/config.js. */
interface RuntimeConfig {
  apiBase?: string;
}

interface Window {
  __CONFIG__?: RuntimeConfig;
}
