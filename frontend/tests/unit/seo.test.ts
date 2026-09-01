/**
 * Тесты разметки для поисковиков.
 *
 * Разметка должна повторять то, что видит человек, и не выдумывать адресов,
 * которых ей не сообщили.
 */

import { describe, expect, it } from "vitest";

import { QUESTIONS } from "~/i18n/faq.ru";
import { structuredData } from "~/seo";

interface Graph {
  "@graph": {
    "@type": string;
    url?: string;
    image?: string;
    mainEntity?: { name: string; acceptedAnswer: { text: string } }[];
  }[];
}

function parse(siteUrl: string): Graph {
  return JSON.parse(structuredData(siteUrl)) as Graph;
}

describe("structuredData", () => {
  it("описывает сайт, игру и вопросы", () => {
    expect(parse("")["@graph"].map((item) => item["@type"])).toEqual([
      "WebSite",
      "VideoGame",
      "FAQPage",
    ]);
  });

  it("вопросы совпадают с теми, что показаны на странице", () => {
    const faq = parse("")["@graph"].find((item) => item["@type"] === "FAQPage");

    expect(faq?.mainEntity).toHaveLength(QUESTIONS.length);
    expect(faq?.mainEntity?.map((item) => item.name)).toEqual(
      QUESTIONS.map((item) => item.question),
    );
    expect(faq?.mainEntity?.map((item) => item.acceptedAnswer.text)).toEqual(
      QUESTIONS.map((item) => item.answer),
    );
  });

  it("без адреса сайта абсолютных ссылок не выдумывает", () => {
    const graph = parse("")["@graph"];

    expect(graph.some((item) => item.url !== undefined)).toBe(false);
    expect(graph.some((item) => item.image !== undefined)).toBe(false);
  });

  it("с адресом сайта проставляет ссылки", () => {
    const graph = parse("https://example.test")["@graph"];

    expect(graph[0]?.url).toBe("https://example.test/");
    expect(graph[1]?.image).toBe("https://example.test/og.png");
  });
});
