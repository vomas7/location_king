/**
 * Политика безопасности и карта.
 *
 * Тайлы OpenStreetMap — единственное, что страница берёт со стороннего домена,
 * и разрешение на них записано в CSP руками, в конфигурации nginx. Стоит
 * OpenLayers сменить адрес тайлов — и карта в проде станет чёрной, а в
 * разработке останется целой: у dev-сервера заголовка CSP нет.
 *
 * Поэтому адрес спрашиваем у самого OpenLayers и сверяем с политикой.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import OSM from "ol/source/OSM";
import { describe, expect, it } from "vitest";

// От каталога frontend, откуда запускается vitest: в окружении jsdom
// import.meta.url — не файловый адрес, и построить путь от него нельзя
const CONFIG = resolve(process.cwd(), "../nginx/snippets/site.conf");

/** Значения одной директивы CSP из конфигурации nginx. */
function directive(name: string): string[] {
  const config = readFileSync(CONFIG, "utf8");
  const policy = /add_header Content-Security-Policy "([^"]+)"/.exec(config);

  expect(policy, "в конфигурации nginx нет заголовка Content-Security-Policy").not.toBeNull();

  const found = (policy?.[1] ?? "")
    .split(";")
    .map((part) => part.trim().split(/\s+/))
    .find((parts) => parts[0] === name);

  expect(found, `в CSP нет директивы ${name}`).toBeDefined();
  return (found ?? []).slice(1);
}

/** Покрывает ли источник CSP конкретный адрес. Звёздочка — только поддомены. */
function allows(sources: string[], url: string): boolean {
  const { origin, host, protocol } = new URL(url);

  return sources.some((source) => {
    if (source === origin || source === host) return true;
    if (!source.startsWith("https://*.")) return false;

    const suffix = source.slice("https://*.".length);
    return protocol === "https:" && host.endsWith(`.${suffix}`);
  });
}

describe("CSP и тайлы карты", () => {
  const urls = new OSM().getUrls() ?? [];

  it("OpenLayers сообщает хотя бы один адрес тайлов", () => {
    expect(urls.length).toBeGreaterThan(0);
  });

  it("img-src разрешает все адреса, по которым OpenLayers берёт тайлы", () => {
    const sources = directive("img-src");

    for (const template of urls) {
      const url = template
        .replace("{z}", "3")
        .replace("{x}", "4")
        .replace("{y}", "5")
        .replace(/\{[a-z-]+\}/, "a");

      expect(allows(sources, url), `${url} не разрешён политикой img-src`).toBe(true);
    }
  });

  it("шаблон со звёздочкой не покрывает домен без поддомена", () => {
    // Ровно та ошибка, из-за которой карта была чёрной в проде
    expect(
      allows(["https://*.tile.openstreetmap.org"], "https://tile.openstreetmap.org/3/4/5.png"),
    ).toBe(false);
  });
});
