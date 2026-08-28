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

import { useEffect, useState } from "react";

import { game, zones } from "~/api/endpoints";
import type {
  DailyChallenge as DailyChallengeData,
  SessionState,
  StartSessionOptions,
} from "~/api/types";
import { DailyChallenge } from "~/components/home/DailyChallenge";
import { DuelSearch } from "~/components/home/DuelSearch";
import { Friends } from "~/components/home/Friends";
import { GameHistory } from "~/components/home/GameHistory";
import styles from "~/components/home/HomeScreen.module.css";
import { Leaderboard } from "~/components/home/Leaderboard";
import { MatchRoom } from "~/components/home/MatchRoom";
import type { Mode, ModeKey } from "~/components/home/ModeBoard";
import { ModeBoard } from "~/components/home/ModeBoard";
import { ProfilePanel } from "~/components/home/ProfilePanel";
import { SoloPanel } from "~/components/home/SoloPanel";
import { Button } from "~/components/ui/Button";
import { Card } from "~/components/ui/Card";
import { searchingText } from "~/domain/duel";
import { formatNumber, plural } from "~/domain/format";
import { FIRST_GAME_SETUP, isNewPlayer } from "~/domain/onboarding";
import { placeFilter } from "~/domain/place";
import { roomFromSearch } from "~/domain/room";
import type { GameSetup } from "~/domain/setup";
import { DEFAULT_SETUP, describeSetup, LEVELS, toOptions } from "~/domain/setup";
import type { LegalDocumentId } from "~/legal/documents";
import { useAuth } from "~/state/authContext";
import { useDailyChallenge } from "~/state/useDailyChallenge";
import { useDuelSearch } from "~/state/useDuelSearch";

/** Разделы, которые смотрят, а не играют. */
type SectionKey = "profile" | "friends" | "board" | "history";

const SECTIONS: { key: SectionKey; label: string }[] = [
  { key: "profile", label: "Профиль" },
  { key: "friends", label: "Друзья" },
  { key: "board", label: "Таблица" },
  { key: "history", label: "История" },
];

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
  const { user } = useAuth();

  // Первую партию настраивать не за что: человек ещё не знает, чем «средне»
  // отличается от «сложно», и первый же непонятный кадр он закрывает
  const newcomer = isNewPlayer(user);

  const [setup, setSetup] = useState<GameSetup>(newcomer ? FIRST_GAME_SETUP : DEFAULT_SETUP);

  // Пришли по ссылке-приглашению — открываем комнату, а не одиночную партию.
  // Считается один раз при создании состояния: сама комната уберёт параметр
  // из адреса, и второй раз его уже не увидеть
  const [mode, setMode] = useState<ModeKey>(() =>
    roomFromSearch(window.location.search) === null ? "solo" : "room",
  );
  const [section, setSection] = useState<SectionKey>("profile");

  const [zoneCount, setZoneCount] = useState<number | null>(null);
  const [unfinished, setUnfinished] = useState<SessionState | null>(null);

  const duel = useDuelSearch(onResume);
  const daily = useDailyChallenge(refreshKey);

  const duelError = duel.error;

  useEffect(() => {
    if (duelError !== null) onError(duelError);
  }, [duelError, onError]);

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

  if (user === null) return null;

  const modes: Mode[] = [
    {
      key: "solo",
      name: "Одиночная",
      status: `${String(setup.rounds)} ${plural(setup.rounds, "раунд", "раунда", "раундов")} · ${
        LEVELS.find((level) => level.value === setup.level)?.label ?? setup.level
      }`,
      live: false,
    },
    {
      key: "daily",
      name: "Челлендж дня",
      status: dailyStatus(daily),
      live: daily !== null && daily.my_session?.status !== "finished",
    },
    {
      key: "duel",
      name: "Дуэль",
      status: searchingText(duel.searching, duel.phase !== "idle"),
      live: duel.phase !== "idle" || duel.searching > 0,
    },
    {
      key: "room",
      name: "Комната",
      status: "Своей компанией по коду",
      live: false,
    },
  ];

  return (
    <div className={styles.screen}>
      <div className={styles.column}>
        {unfinished !== null && (
          <div className={styles.resume}>
            <div>
              <p className={styles.resumeText}>У тебя есть незаконченная партия</p>
              <p className={styles.resumeHint}>
                Раунд {unfinished.session.rounds_done + 1} из {unfinished.session.rounds_total}
              </p>
            </div>
            <Button
              variant="primary"
              onClick={() => {
                onResume(unfinished);
              }}
            >
              Продолжить
            </Button>
          </div>
        )}

        <ModeBoard modes={modes} active={mode} onPick={setMode} />

        <Card id="mode-panel" role="tabpanel" aria-labelledby={`mode-${mode}`}>
          {mode === "solo" && (
            <SoloPanel
              setup={setup}
              onChange={(change) => {
                setSetup({ ...setup, ...change });
              }}
              zoneCount={zoneCount}
              error={error}
              newcomer={newcomer}
              onStart={() => {
                onStart(toOptions(setup));
              }}
            />
          )}

          {mode === "daily" && (
            <DailyChallenge data={daily} onStarted={onResume} onError={onError} />
          )}

          {mode === "duel" && <DuelSearch search={duel} />}

          {mode === "room" && (
            <MatchRoom
              options={toOptions(setup)}
              summary={describeSetup(setup)}
              refreshKey={refreshKey}
              onJoined={onResume}
              onError={onError}
            />
          )}
        </Card>
      </div>

      <div className={styles.column}>
        <div className={styles.sections} role="tablist" aria-label="Разделы">
          {SECTIONS.map((item) => (
            <button
              key={item.key}
              type="button"
              role="tab"
              id={`section-${item.key}`}
              aria-selected={item.key === section}
              aria-controls="section-panel"
              className={[styles.section, item.key === section ? styles.sectionActive : ""]
                .filter(Boolean)
                .join(" ")}
              onClick={() => {
                setSection(item.key);
              }}
            >
              {item.label}
            </button>
          ))}
        </div>

        <Card id="section-panel" role="tabpanel" aria-labelledby={`section-${section}`}>
          {section === "profile" && <ProfilePanel onOpenLegal={onOpenLegal} onError={onError} />}
          {section === "friends" && <Friends onError={onError} />}
          {section === "board" && <Leaderboard refreshKey={refreshKey} />}
          {section === "history" && <GameHistory refreshKey={refreshKey} />}
        </Card>
      </div>
    </div>
  );
}

/** Что написать на плитке челленджа: ради чего в него заходят сегодня. */
function dailyStatus(daily: DailyChallengeData | null): string {
  if (daily === null) return "Одна попытка в сутки";

  if (daily.my_session?.status === "finished") {
    return `Сыгран · ${formatNumber(daily.my_session.total_score)}`;
  }
  if (daily.my_session !== null) return "Партия не доиграна";
  if (daily.current_streak > 0) {
    return `Серия ${String(daily.current_streak)} ${plural(daily.current_streak, "день", "дня", "дней")} — не прерывай`;
  }

  return "Сегодня ещё не сыгран";
}
