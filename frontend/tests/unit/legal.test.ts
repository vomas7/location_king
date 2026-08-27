/**
 * Тесты правовых текстов.
 *
 * Проверяется не юридическая сторона, а то, что документы не разошлись с
 * кодом: политика, обещающая не то, что делает приложение, хуже её
 * отсутствия.
 */

import { describe, expect, it } from "vitest";

import { SESSION_STORAGE_KEY } from "~/api/tokens";
import { NOTICE_STORAGE_KEY } from "~/components/legal/StorageNotice";
import { LEGAL_DOCUMENTS, legalDocument } from "~/legal/documents";

describe("правовые документы", () => {
  it("на месте все три", () => {
    expect(LEGAL_DOCUMENTS.map((document) => document.id)).toEqual(["terms", "privacy", "storage"]);
  });

  it("в каждом разделе есть текст", () => {
    for (const document of LEGAL_DOCUMENTS) {
      expect(document.sections.length).toBeGreaterThan(0);

      for (const section of document.sections) {
        expect(section.heading).not.toBe("");
        const filled = (section.paragraphs?.length ?? 0) + (section.list?.length ?? 0);
        expect(filled, `пустой раздел «${section.heading}»`).toBeGreaterThan(0);
      }
    }
  });

  it("неизвестный документ — это ошибка, а не пустая страница", () => {
    // @ts-expect-error проверяем поведение на значении, которого в типе нет
    expect(() => legalDocument("nothing")).toThrow();
  });
});

describe("документ про хранилище", () => {
  const text = legalDocument("storage")
    .sections.flatMap((section) => [...(section.paragraphs ?? []), ...(section.list ?? [])])
    .join(" ");

  it("называет ровно те ключи, которые приложение и записывает", () => {
    expect(text).toContain(SESSION_STORAGE_KEY);
    expect(text).toContain(NOTICE_STORAGE_KEY);
  });

  it("обещание «куки не ставим» правдиво", () => {
    expect(text).toContain("cookie");
    // Приложение действительно не создаёт ни одного файла cookie
    expect(document.cookie).toBe("");
  });
});

describe("политика конфиденциальности", () => {
  const text = legalDocument("privacy")
    .sections.flatMap((section) => [...(section.paragraphs ?? []), ...(section.list ?? [])])
    .join(" ");

  it("рассказывает про сторонний запрос за картой", () => {
    expect(text).toContain("OpenStreetMap");
  });

  it("говорит про удаление данных", () => {
    expect(text).toContain("Удалить аккаунт");
  });
});
