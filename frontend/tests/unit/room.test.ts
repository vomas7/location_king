import { describe, expect, it } from "vitest";

import {
  CODE_LENGTH,
  isCompleteCode,
  normalizeCode,
  roomFromSearch,
  roomLink,
} from "~/domain/room";

describe("normalizeCode", () => {
  it("приводит к заглавным", () => {
    expect(normalizeCode("ab3k9x")).toBe("AB3K9X");
  });

  it("выкидывает всё, чего в коде быть не может", () => {
    expect(normalizeCode("A B-1 0 I O")).toBe("AB");
  });

  it("обрезает лишнее", () => {
    expect(normalizeCode("ABCDEFGHJK")).toHaveLength(CODE_LENGTH);
  });
});

describe("isCompleteCode", () => {
  it("код набран целиком", () => {
    expect(isCompleteCode("ab3k9x")).toBe(true);
  });

  it("недобранный код не годится", () => {
    expect(isCompleteCode("AB3K9")).toBe(false);
    expect(isCompleteCode("")).toBe(false);
  });
});

describe("roomLink", () => {
  it("собирает приглашение из адреса игры", () => {
    expect(roomLink("AB3K9X", "https://king.example", "/")).toBe(
      "https://king.example/?room=AB3K9X",
    );
  });
});

describe("roomFromSearch", () => {
  it("достаёт код приглашения", () => {
    expect(roomFromSearch("?room=ab3k9x")).toBe("AB3K9X");
  });

  it("без параметра кода нет", () => {
    expect(roomFromSearch("")).toBeNull();
    expect(roomFromSearch("?other=1")).toBeNull();
  });

  it("обрывок кода не считается приглашением", () => {
    expect(roomFromSearch("?room=AB3")).toBeNull();
  });
});
