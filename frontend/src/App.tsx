/**
 * Сборка приложения: какой экран показать и как экраны сменяют друг друга.
 *
 * Роутера нет намеренно: партия — это одно непрерывное состояние, и адрес,
 * по которому можно вернуться в середину раунда, только сбивал бы с толку.
 */

import { useCallback, useState } from "react";

import type { SessionState, StartSessionOptions } from "~/api/types";
import { AuthScreen } from "~/components/auth/AuthScreen";
import { GameScreen } from "~/components/game/GameScreen";
import { RoundResult } from "~/components/game/RoundResult";
import { SummaryScreen } from "~/components/game/SummaryScreen";
import { HomeScreen } from "~/components/home/HomeScreen";
import { TopBar } from "~/components/layout/TopBar";
import { Loader } from "~/components/ui/Loader";
import { Toast } from "~/components/ui/Toast";
import { useAuth } from "~/state/authContext";
import { useGame } from "~/state/useGame";
import { useToast } from "~/state/useToast";

export function App() {
  const { status, user, logout, refresh } = useAuth();
  const { message, show } = useToast();

  // Таблица лидеров и история перечитываются после каждой партии
  const [refreshKey, setRefreshKey] = useState(0);
  const [bestBeforeGame, setBestBeforeGame] = useState(0);

  const onSessionEnd = useCallback(() => {
    void refresh();
    setRefreshKey((value) => value + 1);
  }, [refresh]);

  const game = useGame(onSessionEnd);
  const { state } = game;

  const startGame = useCallback(
    (options: StartSessionOptions) => {
      setBestBeforeGame(user?.best_score ?? 0);
      void game.start(options).catch(() => {
        // Сообщение уже лежит в state.error и показано на главном экране
      });
    },
    [game, user],
  );

  const resumeGame = useCallback(
    (session: SessionState) => {
      setBestBeforeGame(user?.best_score ?? 0);
      game.resume(session);
    },
    [game, user],
  );

  const quitGame = useCallback(() => {
    if (!window.confirm("Завершить партию досрочно?")) return;
    void game.quit();
  }, [game]);

  if (status === "loading") {
    return <Loader text="Восстанавливаем сессию…" />;
  }

  if (status === "anonymous" || user === null) {
    return <AuthScreen />;
  }

  const playing = state.phase === "playing" || state.phase === "result";
  const progress =
    playing && state.session !== null && state.round !== null
      ? {
          roundIndex: state.round.index,
          roundsTotal: state.session.rounds_total,
          score: state.session.total_score,
        }
      : null;

  return (
    <>
      <TopBar
        playerName={user.display_name ?? user.username}
        progress={progress}
        {...(playing ? { onQuit: quitGame } : {})}
        onLogout={() => {
          game.reset();
          logout();
        }}
      />

      {(state.phase === "idle" || state.phase === "loading") && (
        <HomeScreen
          error={state.error}
          onStart={startGame}
          onResume={resumeGame}
          onError={show}
          refreshKey={refreshKey}
        />
      )}

      {playing && state.round !== null && (
        <GameScreen
          round={state.round}
          guess={state.guess}
          busy={state.phase !== "playing"}
          onPick={game.pick}
          onSubmit={() => {
            void game.submit();
          }}
        />
      )}

      {state.phase === "result" && state.lastResult !== null && (
        <RoundResult
          result={state.lastResult}
          isLastRound={state.pendingRound === null}
          onNext={game.advance}
        />
      )}

      {state.phase === "finished" && state.session !== null && (
        <SummaryScreen
          session={state.session}
          results={state.results}
          previousBest={bestBeforeGame}
          {...(state.session.challenge_day === null
            ? {}
            : { challengeDay: state.session.challenge_day })}
          onPlayAgain={() => {
            game.reset();
            show("Настрой партию и жми «Начать»");
          }}
          onHome={game.reset}
        />
      )}

      {state.phase === "loading" && <Loader text={state.loadingText} />}
      {message !== null && <Toast message={message} />}
    </>
  );
}
