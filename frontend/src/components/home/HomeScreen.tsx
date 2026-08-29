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
import { plural } from "~/domain/format";
import { SECTIONS } from "~/domain/menu";
import { FIRST_GAME_SETUP, isNewPlayer } from "~/domain/onboarding";
import { placeFilter } from "~/domain/place";
import { roomFromSearch } from "~/domain/room";
import { DEFAULT_SETUP, describeSetup, LEVELS, toOptions } from "~/domain/setup";
import type { LegalDocumentId } from "~/legal/documents";
import { useAuth } from "~/state/authContext";
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
  const { user } = useAuth();

  // Первую партию настраивать не за что: человек ещё не знает, чем «средне»
  // отличается от «сложно», и первый же непонятный кадр он закрывает
  const newcomer = isNewPlayer(user);

  const { menu, change } = useMenuState(newcomer ? FIRST_GAME_SETUP : DEFAULT_SETUP);
  const { setup, mode, section } = menu;

  // Настройки развёрнуты — состояние одного посещения: открывать их при
  // каждом заходе в меню незачем, а вот прийти в них из комнаты нужно
  const [setupOpen, setSetupOpen] = useState(false);

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

    return window.confirm(
      `Незаконченная партия (раунд ${String(rounds_done + 1)} из ${String(rounds_total)}) ` +
        "будет брошена, и очки за неё не засчитаются. Начать новую?",
    );
  }, [unfinished]);

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
      live: dailyAwaits(daily),
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
              open={setupOpen}
              onToggle={() => {
                setSetupOpen(!setupOpen);
              }}
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
              summary={describeSetup(setup)}
              refreshKey={refreshKey}
              mayStart={mayReplaceGame}
              onEditSetup={() => {
                setSetupOpen(true);
                change({ mode: "solo" });
              }}
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
                change({ section: item.key });
                reveal(sectionPanel.current);
              }}
            >
              {item.label}
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
