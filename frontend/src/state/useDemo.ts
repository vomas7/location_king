/**
 * Ход знакомства с игрой.
 *
 * Отдельно от useGame, потому что это разные вещи: там партия с сессией на
 * сервере, здесь пять заранее известных раундов и ничего, что переживёт
 * закрытие вкладки. Общее у них — правила, а они целиком на сервере.
 *
 * Раунды приезжают все сразу и дальше листаются на месте: сервер о том, где
 * гость сейчас, не знает и знать не должен.
 */

import { useCallback, useReducer } from "react";

import { errorMessage } from "~/api/client";
import { demo } from "~/api/endpoints";
import type { Answer, RoundResult, RoundView } from "~/api/types";
import { useText } from "~/state/languageContext";

/** Что показывает экран знакомства. */
export type DemoPhase =
  | "idle" // ещё не начинали
  | "loading" // ждём ответа сервера
  | "playing" // раунд открыт, гость отвечает
  | "result" // раунд сыгран, показываем, где была цель
  | "finished"; // все раунды пройдены, зовём заводить учётную запись

export interface DemoState {
  phase: DemoPhase;
  /** Все раунды знакомства. Приезжают одним запросом в самом начале */
  rounds: RoundView[];
  /** Номер текущего раунда в rounds, начиная с нуля */
  position: number;
  guess: Answer | null;
  results: RoundResult[];
  lastResult: RoundResult | null;
  error: string | null;
}

type Action =
  | { type: "loading" }
  | { type: "failed"; error: string }
  | { type: "opened"; rounds: RoundView[] }
  | { type: "picked"; guess: Answer }
  | { type: "guessed"; result: RoundResult }
  | { type: "advanced" }
  | { type: "reset" };

const INITIAL: DemoState = {
  phase: "idle",
  rounds: [],
  position: 0,
  guess: null,
  results: [],
  lastResult: null,
  error: null,
};

function reducer(state: DemoState, action: Action): DemoState {
  switch (action.type) {
    case "loading":
      return { ...INITIAL, phase: "loading" };

    case "failed":
      return {
        ...state,
        phase: state.rounds.length === 0 ? "idle" : "playing",
        error: action.error,
      };

    case "opened":
      return { ...INITIAL, phase: "playing", rounds: action.rounds };

    case "picked":
      return { ...state, guess: action.guess };

    case "guessed":
      return {
        ...state,
        phase: "result",
        results: [...state.results, action.result],
        lastResult: action.result,
        error: null,
      };

    case "advanced": {
      const next = state.position + 1;

      if (next >= state.rounds.length) {
        return { ...state, phase: "finished", guess: null };
      }

      return { ...state, phase: "playing", position: next, guess: null };
    }

    case "reset":
      return INITIAL;
  }
}

export interface DemoController {
  state: DemoState;
  /** Раунд, который сейчас на экране. Пусто до начала и после конца */
  round: RoundView | null;
  /** Последний ли это раунд знакомства */
  isLastRound: boolean;
  /** Сумма очков за пройденные раунды */
  totalScore: number;
  start: () => Promise<void>;
  pick: (guess: Answer) => void;
  submit: () => Promise<void>;
  advance: () => void;
  reset: () => void;
}

export function useDemo(): DemoController {
  const { game: text } = useText();
  const [state, dispatch] = useReducer(reducer, INITIAL);

  const round = state.rounds[state.position] ?? null;

  const start = useCallback(async () => {
    dispatch({ type: "loading" });

    try {
      const opened = await demo.rounds();

      if (opened.rounds.length === 0) {
        dispatch({ type: "failed", error: text.noRound });
        return;
      }

      dispatch({ type: "opened", rounds: opened.rounds });
    } catch (error) {
      dispatch({ type: "failed", error: errorMessage(error) });
    }
  }, [text.noRound]);

  const pick = useCallback((guess: Answer) => {
    dispatch({ type: "picked", guess });
  }, []);

  const submit = useCallback(async () => {
    if (round === null || state.guess === null) return;

    try {
      dispatch({ type: "guessed", result: await demo.guess(round.index, state.guess) });
    } catch (error) {
      dispatch({ type: "failed", error: errorMessage(error) });
    }
  }, [round, state.guess]);

  const advance = useCallback(() => {
    dispatch({ type: "advanced" });
  }, []);

  const reset = useCallback(() => {
    dispatch({ type: "reset" });
  }, []);

  return {
    state,
    round,
    isLastRound: state.rounds.length > 0 && state.position === state.rounds.length - 1,
    totalScore: state.results.reduce((sum, result) => sum + result.score, 0),
    start,
    pick,
    submit,
    advance,
    reset,
  };
}
