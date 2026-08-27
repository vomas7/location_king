import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import type { HtmlTagDescriptor, Plugin } from "vite";
import { defineConfig } from "vitest/config";

import { structuredData } from "./src/seo";

/** Куда dev-сервер проксирует /api. В docker-compose это имя сервиса. */
const API_PROXY = process.env.VITE_API_PROXY ?? "http://localhost:8000";

/**
 * Адрес сайта. Нужен там, где ссылка обязана быть абсолютной: canonical,
 * og:url, sitemap. Не задан — эти теги просто не появятся: неверный адрес в
 * canonical хуже отсутствующего, поисковик по нему склеит не те страницы.
 */
const SITE_URL = (process.env.SITE_URL ?? "").replace(/\/+$/, "");

/**
 * Разметка для поисковиков.
 *
 * JSON-LD вставляется блоком данных, а не скриптом: браузер его не исполняет,
 * поэтому строгая CSP со script-src 'self' ему не мешает.
 */
function seoPlugin(): Plugin {
  return {
    name: "location-king-seo",

    transformIndexHtml() {
      const tags: HtmlTagDescriptor[] = [
        {
          tag: "script",
          attrs: { type: "application/ld+json" },
          children: structuredData(SITE_URL),
          injectTo: "head",
        },
      ];

      if (SITE_URL !== "") {
        tags.push(
          { tag: "link", attrs: { rel: "canonical", href: `${SITE_URL}/` }, injectTo: "head" },
          {
            tag: "meta",
            attrs: { property: "og:url", content: `${SITE_URL}/` },
            injectTo: "head",
          },
          {
            tag: "meta",
            attrs: { property: "og:image", content: `${SITE_URL}/og.png` },
            injectTo: "head",
          },
        );
      }

      return tags;
    },

    generateBundle() {
      this.emitFile({
        type: "asset",
        fileName: "robots.txt",
        source:
          "# Индексировать можно всё: игра — одна страница, закрытых разделов нет.\n" +
          "User-agent: *\n" +
          "Allow: /\n\n" +
          "# Адреса API поисковику не нужны: там нет содержания для людей.\n" +
          "Disallow: /api/\n" +
          (SITE_URL === "" ? "" : `\nSitemap: ${SITE_URL}/sitemap.xml\n`),
      });

      if (SITE_URL === "") return;

      this.emitFile({
        type: "asset",
        fileName: "sitemap.xml",
        source:
          '<?xml version="1.0" encoding="UTF-8"?>\n' +
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          `  <url><loc>${SITE_URL}/</loc><changefreq>daily</changefreq></url>\n` +
          "</urlset>\n",
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), seoPlugin()],

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

  test: {
    environment: "jsdom",
    include: ["tests/unit/**/*.test.{ts,tsx}"],
    globals: true,
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
