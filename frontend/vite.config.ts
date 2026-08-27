import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

/** Куда dev-сервер проксирует /api. В docker-compose это имя сервиса. */
const API_PROXY = process.env.VITE_API_PROXY ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],

  resolve: {
    alias: { "~": fileURLToPath(new URL("./src", import.meta.url)) },
  },

  build: {
    assetsDir: "assets",
    sourcemap: true,
    rollupOptions: {
      output: {
        // OpenLayers весит больше остального кода и меняется куда реже —
        // отдельный чанк переживает деплои в кеше браузера
        manualChunks: { ol: ["ol"] },
      },
    },
  },

  server: {
    host: true,
    port: 5173,
    // В разработке API берётся с того же origin, что и в проде
    proxy: {
      "/api": { target: API_PROXY, changeOrigin: true },
    },
  },
});
