/**
 * Подсказки первого раунда.
 *
 * Проверяется главное их свойство: шаг следует за действиями игрока, а не за
 * нажатиями на саму подсказку.
 */

import { fireEvent, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FirstRoundCoach } from "~/components/game/FirstRoundCoach";

import { renderWithLanguage as render } from "./withLanguage";

/**
 * jsdom не знает про matchMedia, а подсказка спрашивает у него, есть ли
 * курсор: на телефоне карта открывается кнопкой, и текст там другой.
 */
function withPointer(hover: boolean): void {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: (query: string) => ({
      matches: hover,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }),
  });
}

afterEach(() => {
  Reflect.deleteProperty(window, "matchMedia");
});

describe("FirstRoundCoach", () => {
  it("начинает с рассказа о снимке", () => {
    withPointer(true);
    render(<FirstRoundCoach mapOpen={false} hasGuess={false} mode="point" onDismiss={vi.fn()} />);

    expect(screen.getByText("Осмотрись")).toBeTruthy();
    expect(screen.getByText("Шаг 1 из 3")).toBeTruthy();
  });

  it("после «Понятно» зовёт поставить точку", () => {
    withPointer(true);
    render(<FirstRoundCoach mapOpen={false} hasGuess={false} mode="point" onDismiss={vi.fn()} />);

    fireEvent.click(screen.getByText("Понятно"));

    expect(screen.getByText("Отметь место")).toBeTruthy();
    expect(screen.queryByText("Понятно")).toBeNull();
  });

  it("на телефоне зовёт нажать кнопку, а не подвести курсор", () => {
    withPointer(false);
    render(<FirstRoundCoach mapOpen={false} hasGuess={false} mode="point" onDismiss={vi.fn()} />);

    fireEvent.click(screen.getByText("Понятно"));

    expect(screen.getByText(/Нажми «Открыть карту»/)).toBeTruthy();
    expect(screen.queryByText(/Подведи курсор/)).toBeNull();
  });

  it("поставленная точка сразу переводит к ответу", () => {
    withPointer(true);
    render(<FirstRoundCoach mapOpen={false} hasGuess mode="point" onDismiss={vi.fn()} />);

    expect(screen.getByText("Отвечай")).toBeTruthy();
    expect(screen.getByText("Шаг 3 из 3")).toBeTruthy();
  });

  it("раскрытая карта снимает шаг о том, как её раскрыть", () => {
    withPointer(false);
    const { rerender } = render(
      <FirstRoundCoach mapOpen={false} hasGuess={false} mode="point" onDismiss={vi.fn()} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Понятно" }));
    expect(screen.getByRole("heading", { name: "Отметь место" })).toBeTruthy();

    rerender(<FirstRoundCoach mapOpen hasGuess={false} mode="point" onDismiss={vi.fn()} />);

    expect(screen.getByRole("heading", { name: "Отвечай" })).toBeTruthy();
    expect(screen.queryByText(/Нажми «Открыть карту»/)).toBeNull();
  });

  it("подсказки можно закрыть", () => {
    withPointer(true);
    const onDismiss = vi.fn();
    render(<FirstRoundCoach mapOpen={false} hasGuess={false} mode="point" onDismiss={onDismiss} />);

    fireEvent.click(screen.getByText("Не показывать"));

    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});

describe("подсказка в раунде про страны", () => {
  it("зовёт выбрать страну, а не ставить точку", () => {
    withPointer(true);
    render(<FirstRoundCoach mapOpen={false} hasGuess={false} mode="country" onDismiss={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Понятно" }));

    expect(screen.getByRole("heading", { name: "Выбери страну" })).toBeTruthy();
  });

  it("не обещает очков за близость: их здесь не дают", () => {
    withPointer(true);
    render(<FirstRoundCoach mapOpen={false} hasGuess mode="country" onDismiss={vi.fn()} />);

    expect(screen.getByText(/угадал — все пять тысяч/i)).toBeTruthy();
    expect(screen.queryByText(/чем ближе к цели/i)).toBeNull();
  });
});

describe("подсказка в простом режиме", () => {
  it("зовёт выбрать из списка, а не открывать карту", () => {
    withPointer(false);
    render(<FirstRoundCoach mapOpen={false} hasGuess={false} mode="choice" onDismiss={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Понятно" }));

    expect(screen.getByText(/Под снимком шесть стран/)).toBeTruthy();
    expect(screen.queryByText(/карт/i)).toBeNull();
  });
});
