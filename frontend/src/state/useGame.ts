/**
 * Ход партии.
 *
 * Правила игры целиком на сервере: здесь только то, что сейчас на экране, и
 * переходы между этими состояниями.
 */

import { useCallback, useReducer } from "react";

import { errorMessage } from "~/api/client";
import { game } from "~/api/endpoints";
import type {
  RoundResult,
  RoundView,
  SessionState,
  SessionView,
  StartSessionOptions,
} from "~/api/types";
import type { LonLat } from "~/map/guess";

/** Что показывает экран игры. */
export type GamePhase =
  | "idle" // партии нет
  | "loading" // ждём ответа сервера
  | "playing" // раунд открыт, игрок ставит точку
  | "result" // раунд сыгран, показываем, где была цель
  | "finished"; // партия окончена

export interface GameState {
  phase: GamePhase;
  /** Условия, с которыми начали партию. Пусто у продолженной: их уже не узнать */
  options: StartSessionOptions | null;
  session: SessionView | null;
  round: RoundView | null;
  guess: LonLat | null;
  results: RoundResult[];
  lastResult: RoundResult | null;
  pendingRound: RoundView | null;
  loadingText: string;
  error: string | null;
}

type Action =
  | { type: "loading"; text: string }
  | { type: "failed"; error: string }
  | {
      type: "opened";
      session: SessionView;
      round: RoundView;
      results: RoundResult[];
      options: StartSessionOptions | null;
    }
  | { type: "picked"; guess: LonLat }
  | { type: "hinted"; round: RoundView }
  | { type: "guessed"; session: SessionView; result: RoundResult; next: RoundView | null }
  | { type: "advanced" }
  | { type: "finished"; session: SessionView; results: RoundResult[] }
  | { type: "reset" };

const INITIAL: GameState = {
  phase: "idle",
  options: null,
  session: null,
  round: null,
  guess: null,
  results: [],
  lastResult: null,
  pendingRound: null,
  loadingText: "",
  error: null,
};

function reducer(state: GameState, action: Action): GameState {
  switch (action.type) {
    case "loading":
      return { ...state, phase: "loading", loadingText: action.text, error: null };

    case "failed":
      return { ...state, phase: state.round === null ? "idle" : "playing", error: action.error };

    case "opened":
      return {
        ...state,
        phase: "playing",
        options: action.options,
        session: action.session,
        round: action.round,
        results: action.results,
        guess: null,
        lastResult: null,
        pendingRound: null,
        error: null,
      };

    case "picked":
      return { ...state, guess: action.guess };

    case "hinted":
      return { ...state, round: action.round, error: null };

    case "guessed":
      return {
        ...state,
        phase: "result",
        session: action.session,
        results: [...state.results, action.result],
        lastResult: action.result,
        pendingRound: action.next,
        error: null,
      };

    case "advanced": {
      if (state.pendingRound === null) {
        return { ...state, phase: "finished" };
      }
      return {
        ...state,
        phase: "playing",
        round: state.pendingRound,
        pendingRound: null,
        guess: null,
      };
    }

    case "finished":
      return {
        ...state,
        phase: "finished",
        session: action.session,
        results: action.results,
        round: null,
        guess: null,
      };

    case "reset":
      return INITIAL;
  }
}

export interface GameController {
  state: GameState;
  start: (options: StartSessionOptions) => Promise<void>;
  resume: (session: SessionState) => void;
  pick: (guess: LonLat) => void;
  /** Взять подсказку по текущему раунду. */
  hint: () => Promise<void>;
  submit: () => Promise<void>;
  /** Закрыть раунд, на который не успели ответить. */
  timeout: () => Promise<void>;
  advance: () => void;
  quit: () => Promise<void>;
  reset: () => void;
}

export function useGame(onSessionEnd: () => void): GameController {
  const [state, dispatch] = useReducer(reducer, INITIAL);

  const start = useCallback(async (options: StartSessionOptions) => {
    dispatch({ type: "loading", text: "Выбираем место…" });

    try {
      const opened = await game.start(options);
      if (opened.current_round === null) {
        dispatch({ type: "failed", error: "Сервер не выдал раунд" });
        return;
      }

      dispatch({
        type: "opened",
        session: opened.session,
        round: opened.current_round,
        results: opened.results,
        options,
      });
    } catch (error) {
      dispatch({ type: "failed", error: errorMessage(error) });
      throw error;
    }
  }, []);

  const resume = useCallback((session: SessionState) => {
    if (session.current_round === null) return;

    dispatch({
      type: "opened",
      session: session.session,
      round: session.current_round,
      results: session.results,
      // Продолженная партия про свои условия уже не знает: их выбирали в
      // прошлый раз и никуда не сохраняли
      options: null,
    });
  }, []);

  const pick = useCallback((guess: LonLat) => {
    dispatch({ type: "picked", guess });
  }, []);

  // Подсказка не перекрывает экран загрузкой: она меняет один блок в панели,
  // а снимок и поставленная точка остаются на месте
  const hint = useCallback(async () => {
    const round = state.round;
    if (state.phase !== "playing" || round === null || round.hint !== null) return;

    try {
      dispatch({ type: "hinted", round: await game.hint(round.id) });
    } catch (error) {
      dispatch({ type: "failed", error: errorMessage(error) });
    }
  }, [state.phase, state.round]);

  const submit = useCallback(async () => {
    // Ответ может прийти и от кнопки, и от истёкшего таймера. Раунд
    // закрывается один раз: второй запрос сервер всё равно отклонит, а на
    // экране вместо результата появилась бы ошибка.
    if (state.phase !== "playing" || state.round === null || state.guess === null) return;

    dispatch({ type: "loading", text: "Считаем расстояние…" });

    try {
      const response = await game.guess(
        state.round.id,
        state.guess.longitude,
        state.guess.latitude,
      );

      dispatch({
        type: "guessed",
        session: response.session,
        result: response.result,
        next: response.next_round,
      });

      if (response.is_session_finished) onSessionEnd();
    } catch (error) {
      dispatch({ type: "failed", error: errorMessage(error) });
    }
  }, [state.phase, state.round, state.guess, onSessionEnd]);

  const timeout = useCallback(async () => {
    if (state.phase !== "playing" || state.round === null) return;

    dispatch({ type: "loading", text: "Время вышло…" });

    try {
      const response = await game.timeout(state.round.id);

      dispatch({
        type: "guessed",
        session: response.session,
        result: response.result,
        next: response.next_round,
      });

      if (response.is_session_finished) onSessionEnd();
    } catch (error) {
      dispatch({ type: "failed", error: errorMessage(error) });
    }
  }, [state.phase, state.round, onSessionEnd]);

  const advance = useCallback(() => {
    dispatch({ type: "advanced" });
  }, []);

  const quit = useCallback(async () => {
    if (state.session === null) return;

    dispatch({ type: "loading", text: "Подводим итоги…" });

    try {
      const closed = await game.finish(state.session.id);
      dispatch({ type: "finished", session: closed.session, results: closed.results });
      onSessionEnd();
    } catch (error) {
      dispatch({ type: "failed", error: errorMessage(error) });
    }
  }, [state.session, onSessionEnd]);

  const reset = useCallback(() => {
    dispatch({ type: "reset" });
  }, []);

  return { state, start, resume, pick, hint, submit, timeout, advance, quit, reset };
}
