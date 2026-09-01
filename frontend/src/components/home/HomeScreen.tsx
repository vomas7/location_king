/**
 * Меню перед игрой.
 *
 * Раньше это был столбец из девяти карточек: чтобы дойти от «начать партию»
 * до таблицы лидеров, на телефоне приходилось листать полтора экрана мимо
 * всего остального. Теперь на экране два выбора, и каждый раскрывает ровно
 * одну панель: чем играть — и что смотреть. Всё остальное свёрнуто, но
 * названо, поэтому ничего не пропадает.
 *
 * Поиск дуэли живёт здесь, а не в своей панели: очередь не должна
 * обрываться от того, что игрок ушёл смотреть таблицу.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { game, zones } from "~/api/endpoints";
import type { SessionState, StartSessionOptions } from "~/api/types";
import { DailyChallenge } from "~/components/home/DailyChallenge";
import { DuelSearch } from "~/components/home/DuelSearch";
import { Friends } from "~/components/home/Friends";
import { GameHistory } from "~/components/home/GameHistory";
import { LandmarksPanel } from "~/components/home/LandmarksPanel";
import styles from "~/components/home/HomeScreen.module.css";
import { Leaderboard } from "~/components/home/Leaderboard";
import { MatchRoom } from "~/components/home/MatchRoom";
import type { Mode } from "~/components/home/ModeBoard";
import { ModeBoard } from "~/components/home/ModeBoard";
import { ProfilePanel } from "~/components/home/ProfilePanel";
import { SoloPanel } from "~/components/home/SoloPanel";
import { Button } from "~/components/ui/Button";
import { Card } from "~/components/ui/Card";
import { dailyAwaits, dailyStatus } from "~/domain/daily";
import { searchingText } from "~/domain/duel";
import { SECTIONS } from "~/domain/menu";
import { FIRST_GAME_SETUP, isNewPlayer } from "~/domain/onboarding";
import { placeFilter } from "~/domain/place";
import { roomFromSearch } from "~/domain/room";
import { DEFAULT_SETUP, describeSetup, toOptions } from "~/domain/setup";
import type { LegalDocumentId } from "~/legal/documents";
import { useAuth } from "~/state/authContext";
import { useFormats, useText } from "~/state/languageContext";
import { useDailyChallenge } from "~/state/useDailyChallenge";
import { useDuelSearch } from "~/state/useDuelSearch";
import { useMenuState } from "~/state/useMenuState";

/**
 * Подтянуть панель раздела к экрану, если её не видно.
 *
 * На телефоне колонки идут одна под другой, и панель раздела оказывается за
 * нижним краем: игрок нажимает «Друзья» и не понимает, что что-то произошло.
 * На широком экране панель и так на виду, и дёргать страницу незачем.
 */
function reveal(panel: HTMLElement | null): void {
  if (panel === null) return;

  // Прокручиваем, когда панель начинается ниже середины экрана: формально она
  // при этом видна, но видно от неё одну шапку
  const { top } = panel.getBoundingClientRect();
  if (top < window.innerHeight / 2) return;

  const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  panel.scrollIntoView({ behavior: still ? "auto" : "smooth", block: "start" });
}

interface HomeScreenProps {
  error: string | null;
  onStart: (options: StartSessionOptions) => void;
  onResume: (session: SessionState) => void;
  onError: (message: string) => void;
  onOpenLegal: (document: LegalDocumentId) => void;
  /** Меняется после каждой партии, чтобы таблица и история перечитались. */
  refreshKey: number;
}

export function HomeScreen({
  error,
  onStart,
  onResume,
  onError,
  onOpenLegal,
  refreshKey,
}: HomeScreenProps) {
  const formats = useFormats();
  const text = useText();
  const { menu: menuText } = text;
  const { user } = useAuth();

  // Первую партию настраивать не за что: человек ещё не знает, чем «средне»
  // отличается от «сложно», и первый же непонятный кадр он закрывает
  const newcomer = isNewPlayer(user);

  const { menu, change } = useMenuState(newcomer ? FIRST_GAME_SETUP : DEFAULT_SETUP);
  const { setup, mode, section } = menu;

  // Панель раздела на телефоне лежит ниже экрана: без прокрутки к ней нажатие
  // по вкладке выглядит так, будто ничего не произошло
  const sectionPanel = useRef<HTMLDivElement>(null);

  const [zoneCount, setZoneCount] = useState<number | null>(null);
  const [unfinished, setUnfinished] = useState<SessionState | null>(null);

  const duel = useDuelSearch(onResume);
  const daily = useDailyChallenge(refreshKey);

  const duelError = duel.error;

  useEffect(() => {
    if (duelError !== null) onError(duelError);
  }, [duelError, onError]);

  // Пришли по ссылке-приглашению — открываем комнату, что бы ни было выбрано
  // в прошлый раз. Сама комната уберёт параметр из адреса, поэтому условие
  // сработает один раз
  useEffect(() => {
    if (roomFromSearch(window.location.search) !== null) change({ mode: "room" });
  }, [change]);

  // Сколько зон под выбранными фильтрами: без этого игрок не понимает, почему
  // «Начать» отвечает, что зон нет
  useEffect(() => {
    let cancelled = false;

    const { continent, country_group } = placeFilter(setup.place);

    const query = new URLSearchParams({ difficulty: setup.level });
    if (continent !== null) query.set("continent", continent);
    if (country_group !== null) query.set("country_group", country_group);

    void (async () => {
      try {
        const found = await zones.list(query.toString());
        if (!cancelled) setZoneCount(found.length);
      } catch {
        if (!cancelled) setZoneCount(null);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [setup.place, setup.level]);

  // Незавершённая партия — предлагаем продолжить, а не начинать заново
  useEffect(() => {
    let cancelled = false;

    void (async () => {
      try {
        const current = await game.current();
        const canResume = current !== null && current.current_round !== null;
        if (!cancelled) setUnfinished(canResume ? current : null);
      } catch {
        if (!cancelled) setUnfinished(null);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  /**
   * Спросить, если новая партия закроет незаконченную.
   *
   * Партия у игрока одна: сервер молча бросает предыдущую, а очки за
   * недоигранную не идут никуда. До этого вопроса партия на четвёртом раунде
   * пропадала от одного нажатия — и в челлендже дня пропадала навсегда,
   * попытка там одна на сутки.
   */
  const mayReplaceGame = useCallback(() => {
    if (unfinished === null) return true;

    const { rounds_done, rounds_total } = unfinished.session;

    return window.confirm(menuText.replaceGame(rounds_done + 1, rounds_total));
  }, [unfinished, menuText]);

  if (user === null) return null;

  const modes: Mode[] = [
    {
      key: "solo",
      name: menuText.solo,
      status: menuText.soloStatus(text.setup.answerModes[setup.answerMode].label, setup.rounds),
      live: false,
    },
    {
      key: "landmarks",
      name: menuText.landmarks,
      status: menuText.landmarksStatus,
      live: false,
    },
    {
      key: "daily",
      name: menuText.daily,
      status: dailyStatus(daily, text, formats),
      live: dailyAwaits(daily),
    },
    {
      key: "duel",
      name: menuText.duel,
      status: searchingText(duel.searching, duel.phase !== "idle", text),
      live: duel.phase !== "idle" || duel.searching > 0,
    },
    {
      key: "room",
      name: menuText.room,
      status: menuText.roomStatus,
      live: false,
    },
  ];

  return (
    <div className={styles.screen}>
      <div className={styles.column}>
        {unfinished !== null && (
          <div className={styles.resume}>
            <div>
              <p className={styles.resumeText}>{menuText.unfinished}</p>
              <p className={styles.resumeHint}>
                {menuText.roundOf(
                  unfinished.session.rounds_done + 1,
                  unfinished.session.rounds_total,
                )}
              </p>
            </div>
            <Button
              variant="primary"
              onClick={() => {
                onResume(unfinished);
              }}
            >
              {menuText.resume}
            </Button>
          </div>
        )}

        <ModeBoard
          modes={modes}
          active={mode}
          onPick={(picked) => {
            change({ mode: picked });
          }}
        />

        <Card id="mode-panel" role="tabpanel" aria-labelledby={`mode-${mode}`}>
          {mode === "solo" && (
            <SoloPanel
              setup={setup}
              onChange={(patch) => {
                change({ setup: { ...setup, ...patch } });
              }}
              zoneCount={zoneCount}
              error={error}
              newcomer={newcomer}
              onStart={() => {
                if (mayReplaceGame()) onStart(toOptions(setup));
              }}
            />
          )}

          {mode === "landmarks" && (
            <LandmarksPanel
              setup={setup}
              onChange={(patch) => {
                change({ setup: { ...setup, ...patch } });
              }}
              error={error}
              onStart={() => {
                if (mayReplaceGame()) onStart(toOptions(setup, "landmark"));
              }}
            />
          )}

          {mode === "daily" && (
            <DailyChallenge
              data={daily}
              mayStart={mayReplaceGame}
              onStarted={onResume}
              onError={onError}
            />
          )}

          {mode === "duel" && <DuelSearch search={duel} mayStart={mayReplaceGame} />}

          {mode === "room" && (
            <MatchRoom
              options={toOptions(setup)}
              summary={describeSetup(setup, text, formats)}
              refreshKey={refreshKey}
              mayStart={mayReplaceGame}
              onEditSetup={() => {
                change({ mode: "solo" });
              }}
              onJoined={onResume}
              onError={onError}
            />
          )}
        </Card>
      </div>

      <div className={styles.column}>
        <div className={styles.sections} role="tablist" aria-label={menuText.sections}>
          {SECTIONS.map((key) => (
            <button
              key={key}
              type="button"
              role="tab"
              id={`section-${key}`}
              aria-selected={key === section}
              aria-controls="section-panel"
              className={[styles.section, key === section ? styles.sectionActive : ""]
                .filter(Boolean)
                .join(" ")}
              onClick={() => {
                change({ section: key });
                reveal(sectionPanel.current);
              }}
            >
              {menuText.section[key]}
            </button>
          ))}
        </div>

        <Card
          ref={sectionPanel}
          id="section-panel"
          role="tabpanel"
          aria-labelledby={`section-${section}`}
        >
          {section === "profile" && <ProfilePanel onOpenLegal={onOpenLegal} onError={onError} />}
          {section === "friends" && <Friends onError={onError} />}
          {section === "board" && <Leaderboard refreshKey={refreshKey} />}
          {section === "history" && <GameHistory refreshKey={refreshKey} />}
        </Card>
      </div>
    </div>
  );
}
