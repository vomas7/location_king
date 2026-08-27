/**
 * Картинка для соцсетей: 1200×630, та же вёрстка и те же шрифты, что у игры.
 *
 * Рисуется браузером и снимается скриншотом, потому что подгонять шрифты и
 * отступы руками в графическом редакторе — работа, которую уже умеет делать
 * движок вёрстки. Запускать после правок оформления:
 *
 *     node scripts/make-og-image.mjs
 */

import { chromium } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { readFileSync } from "node:fs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const fonts = resolve(root, "public/fonts");

/** Шрифт вшивается в страницу: иначе браузеру пришлось бы ходить за файлом. */
function font(name) {
  return `data:font/woff2;base64,${readFileSync(resolve(fonts, name)).toString("base64")}`;
}

const html = `
<!doctype html>
<meta charset="utf-8" />
<style>
  @font-face {
    font-family: Unbounded;
    src: url("${font("unbounded-cyrillic.woff2")}") format("woff2");
    font-weight: 500 800;
  }
  @font-face {
    font-family: Onest;
    src: url("${font("onest-cyrillic.woff2")}") format("woff2");
    font-weight: 400 800;
  }

  * { margin: 0; box-sizing: border-box; }

  body {
    width: 1200px;
    height: 630px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 22px;
    padding: 76px 80px 132px;
    background:
      radial-gradient(700px 420px at 10% -10%, rgb(255 171 46 / 16%), transparent 62%),
      radial-gradient(620px 420px at 96% 110%, rgb(86 199 240 / 10%), transparent 62%),
      #070d0c;
    color: #e6efeb;
    font-family: Onest, sans-serif;
    overflow: hidden;
  }

  .grid {
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(to right, rgb(255 171 46 / 7%) 1px, transparent 1px),
      linear-gradient(to bottom, rgb(255 171 46 / 7%) 1px, transparent 1px);
    background-size: 105px 105px;
    mask-image: radial-gradient(720px 520px at 78% 50%, #000 20%, transparent 78%);
  }

  .eyebrow {
    position: relative;
    color: #ffab2e;
    font-size: 19px;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }

  h1 {
    position: relative;
    max-width: 11ch;
    font-family: Unbounded, sans-serif;
    font-size: 74px;
    font-weight: 800;
    letter-spacing: -0.04em;
    line-height: 0.98;
  }

  p {
    position: relative;
    max-width: 36ch;
    color: #9fb3ad;
    font-size: 24px;
    line-height: 1.45;
  }

  .mark {
    position: absolute;
    top: 50%;
    right: 92px;
    width: 300px;
    height: 300px;
    color: #ffab2e;
    transform: translateY(-50%);
  }

  .brand {
    position: absolute;
    bottom: 54px;
    left: 80px;
    display: flex;
    align-items: center;
    gap: 12px;
    color: #849d96;
    font-size: 20px;
    font-weight: 600;
  }

  .dot { width: 10px; height: 10px; border-radius: 50%; background: #ffab2e; }
</style>

<div class="grid"></div>

<p class="eyebrow">Геогессер по спутниковым снимкам</p>
<h1>Найди точку на планете</h1>
<p>Квадрат съёмки без подписей и координат. Чем ближе поставишь точку, тем больше очков.</p>

<svg class="mark" viewBox="0 0 320 320" fill="none">
  <g stroke="currentColor" stroke-width="3" stroke-linecap="round">
    <circle cx="160" cy="160" r="74" stroke-opacity="0.9" />
    <circle cx="160" cy="160" r="120" stroke-opacity="0.25" />
    <path d="M160 26v60M160 234v60M26 160h60M234 160h60" />
  </g>
  <circle cx="160" cy="160" r="9" fill="currentColor" />
</svg>

<div class="brand"><span class="dot"></span>Location King</div>
`;

const browser = await chromium.launch({
  ...(process.env.PLAYWRIGHT_CHROMIUM_PATH === undefined
    ? {}
    : { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH }),
});

const page = await browser.newPage({ viewport: { width: 1200, height: 630 } });
await page.setContent(html, { waitUntil: "load" });
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: resolve(root, "public/og.png") });
await browser.close();

console.log("public/og.png собран");
