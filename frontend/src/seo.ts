/**
 * Разметка для поисковиков.
 *
 * Собирается из тех же текстов, что показаны на странице: вопросы в JSON-LD и
 * вопросы на экране должны совпадать слово в слово, иначе разметка считается
 * недостоверной. Подставляется в index.html при сборке — Vite-плагин в
 * vite.config.ts.
 */

// Путь относительный, а не через «~»: этот модуль читает ещё и
// vite.config.ts, где псевдонимы Vite пока не действуют
import { QUESTIONS } from "./i18n/faq.ru";

export const SITE_NAME = "Location King";
export const SITE_DESCRIPTION =
  "Геогессер по спутниковым снимкам: показываем квадрат съёмки без подписей и " +
  "координат, а вы ищете это место на карте мира. Челлендж дня, комнаты на " +
  "компанию и таблица лидеров. Бесплатно, без рекламы.";

/**
 * Структурированные данные страницы.
 *
 * @param siteUrl адрес сайта без косой черты на конце. Пустая строка — адрес
 *   неизвестен, и абсолютные ссылки в разметку не попадают: неверный адрес
 *   хуже отсутствующего.
 */
export function structuredData(siteUrl: string): string {
  const absolute = (path: string) => (siteUrl === "" ? undefined : `${siteUrl}${path}`);

  const graph = [
    {
      "@type": "WebSite",
      name: SITE_NAME,
      description: SITE_DESCRIPTION,
      inLanguage: "ru-RU",
      ...(absolute("/") === undefined ? {} : { url: absolute("/") }),
    },
    {
      "@type": "VideoGame",
      name: SITE_NAME,
      description: SITE_DESCRIPTION,
      inLanguage: "ru-RU",
      applicationCategory: "GameApplication",
      gamePlatform: "Веб-браузер",
      operatingSystem: "Любая",
      offers: { "@type": "Offer", price: "0", priceCurrency: "RUB" },
      ...(absolute("/og.png") === undefined ? {} : { image: absolute("/og.png") }),
    },
    {
      "@type": "FAQPage",
      mainEntity: QUESTIONS.map((item) => ({
        "@type": "Question",
        name: item.question,
        acceptedAnswer: { "@type": "Answer", text: item.answer },
      })),
    },
  ];

  return JSON.stringify({ "@context": "https://schema.org", "@graph": graph });
}
