/**
 * Сборка приложения: какой экран показать и как экраны сменяют друг друга.
 *
 * Роутера нет намеренно: партия — это одно непрерывное состояние, и адрес,
 * по которому можно вернуться в середину раунда, только сбивал бы с толку.
 */

import { useCallback, useState } from "react";

import type { SessionState, StartSessionOptions } from "~/api/types";
import { DemoScreen } from "~/components/demo/DemoScreen";
import { GameScreen } from "~/components/game/GameScreen";
import { RoundResult } from "~/components/game/RoundResult";
import { SummaryScreen } from "~/components/game/SummaryScreen";
import { HomeScreen } from "~/components/home/HomeScreen";
import { LandingScreen } from "~/components/landing/LandingScreen";
import { LegalDialog } from "~/components/legal/LegalDialog";
import { StorageNotice } from "~/components/legal/StorageNotice";
import { TopBar } from "~/components/layout/TopBar";
import { Loader } from "~/components/ui/Loader";
import { Toast } from "~/components/ui/Toast";
import { isNewPlayer } from "~/domain/onboarding";
import type { LegalDocumentId } from "~/legal/documents";
import { useAppTheme } from "~/state/useAppTheme";
import { useAuth } from "~/state/authContext";
import { useText } from "~/state/languageContext";
import { useGame } from "~/state/useGame";
import { useToast } from "~/state/useToast";

export function App() {
  const { status, user, logout, refresh } = useAuth();
  const { app } = useText();
  const { message, show } = useToast();

  useAppTheme();

  // Таблица лидеров и история перечитываются после каждой партии
  const [refreshKey, setRefreshKey] = useState(0);
  const [legal, setLegal] = useState<LegalDocumentId | null>(null);
  // Знакомство с игрой: гость его открывает с посадочной страницы, и после
  // него страница показывается уже с открытой вкладкой регистрации
  const [demoOpen, setDemoOpen] = useState(false);
  const [cameFromDemo, setCameFromDemo] = useState(false);
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
    if (!window.confirm(app.quitConfirm)) return;
    void game.quit();
  }, [game, app.quitConfirm]);

  if (status === "loading") {
    return <Loader text={app.restoring} />;
  }

  const closeLegal = () => {
    setLegal(null);
  };

  if (status === "anonymous" || user === null) {
    if (demoOpen) {
      return (
        <main id="main" className="main">
          <DemoScreen
            onLeave={() => {
              setDemoOpen(false);
            }}
            onSignUp={() => {
              setDemoOpen(false);
              setCameFromDemo(true);
            }}
          />
        </main>
      );
    }

    return (
      <>
        <LandingScreen
          onOpenLegal={setLegal}
          signUpFirst={cameFromDemo}
          onPlayDemo={() => {
            setDemoOpen(true);
          }}
        />
        <StorageNotice
          onDetails={() => {
            setLegal("storage");
          }}
        />
        <LegalDialog open={legal} onClose={closeLegal} />
      </>
    );
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
      <a className="skip-link" href="#main">
        {app.toGame}
      </a>

      <TopBar
        playerName={user.display_name ?? user.username}
        playerAvatar={user.avatar}
        progress={progress}
        {...(playing ? { onQuit: quitGame } : {})}
        onLogout={() => {
          game.reset();
          logout();
        }}
      />

      <main id="main" className="main">
        {(state.phase === "idle" || state.phase === "loading") && (
          <HomeScreen
            error={state.error}
            onStart={startGame}
            onResume={resumeGame}
            onError={show}
            onOpenLegal={setLegal}
            refreshKey={refreshKey}
          />
        )}

        {playing && state.round !== null && (
          <GameScreen
            round={state.round}
            guess={state.guess}
            busy={state.phase !== "playing"}
            timeLimitSeconds={state.session?.time_limit_seconds ?? null}
            coaching={isNewPlayer(user) && state.round.index === 1}
            onPick={game.pick}
            onHint={() => {
              void game.hint();
            }}
            onSubmit={() => {
              void game.submit();
            }}
            onTimeout={() => {
              void game.timeout();
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
            options={state.options}
            {...(state.session.challenge_day === null
              ? {}
              : { challengeDay: state.session.challenge_day })}
            onPlayAgain={() => {
              // Условия известны — повторяем их сразу: после партии человек
              // хочет играть, а не настраивать то же самое заново
              if (state.options === null) {
                game.reset();
                show(app.setupHint);
                return;
              }
              startGame(state.options);
            }}
            onHome={game.reset}
          />
        )}
      </main>

      {/* Подвала в меню нет: документы и правообладатели переехали в раздел
          «Профиль». На телефоне подвал занимал экран строками, которые
          открывают раз в жизни */}
      {!playing && (
        <StorageNotice
          onDetails={() => {
            setLegal("storage");
          }}
        />
      )}

      {state.phase === "loading" && <Loader text={state.loadingText} />}
      {message !== null && <Toast message={message} />}

      <LegalDialog open={legal} onClose={closeLegal} />
    </>
  );
}
