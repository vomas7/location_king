/**
 * Комната: та же серия раундов, но для компании.
 *
 * Комната открывается тремя путями — создали, ввели код, пришли по ссылке
 * `?room=CODE`. Дальше все три ведут себя одинаково, поэтому состояние здесь
 * одно: открытая комната либо её нет.
 */

import { useCallback, useEffect, useState } from "react";

import { errorMessage } from "~/api/client";
import { game as gameApi, matches as matchesApi } from "~/api/endpoints";
import type { MatchSummary, MatchView, SessionState, StartSessionOptions } from "~/api/types";
import styles from "~/components/home/MatchRoom.module.css";
import { PlayerRow } from "~/components/ui/PlayerRow";
import { Button } from "~/components/ui/Button";
import { CardSubtitle, CardTitle } from "~/components/ui/Card";
import { CODE_LENGTH, isCompleteCode, normalizeCode } from "~/domain/codes";
import { roomFromSearch, roomLink } from "~/domain/room";
import type { Dictionary } from "~/i18n/dictionary";
import { type ShareState, useShare } from "~/state/useShare";
import { useFormats, useText } from "~/state/languageContext";

interface MatchRoomProps {
  /** Условия одиночной партии: комната собирается по ним же. */
  options: StartSessionOptions;
  /** Те же условия словами — их видно до того, как комната создана. */
  summary: string;
  /** Меняется после каждой партии, чтобы таблица комнаты перечиталась. */
  refreshKey: number;
  /** Спросить, можно ли бросить начатую партию ради комнаты. */
  mayStart: () => boolean;
  /** Уйти в настройки одиночной партии: комната собирается по ним. */
  onEditSetup: () => void;
  onJoined: (session: SessionState) => void;
  onError: (message: string) => void;
}

/** Как часто перечитывать таблицу, пока комната открыта. */
const REFRESH_MS = 10000;

/** Подпись кнопки со ссылкой: она же говорит, что произошло после нажатия */
function linkLabel(state: ShareState, text: Dictionary): string {
  if (state === "copied") return text.room.linkCopied;
  if (state === "failed") return text.room.copyFailed;

  return text.room.copyLink;
}

export function MatchRoom({
  options,
  summary,
  refreshKey,
  mayStart,
  onEditSetup,
  onJoined,
  onError,
}: MatchRoomProps) {
  const formats = useFormats();
  const text = useText();
  const [room, setRoom] = useState<MatchView | null>(null);
  const [mine, setMine] = useState<MatchSummary[]>([]);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);

  const link = useShare();

  const open = useCallback(
    async (wanted: string) => {
      setBusy(true);
      try {
        setRoom(await matchesApi.get(wanted));
      } catch (error) {
        onError(errorMessage(error, text.room.notFound));
      } finally {
        setBusy(false);
      }
    },
    [onError, text.room.notFound],
  );

  // Пришли по ссылке-приглашению. Параметр сразу убираем: он нужен один раз, а
  // после перезагрузки страницы только сбивал бы с толку
  useEffect(() => {
    const invited = roomFromSearch(window.location.search);
    if (invited === null) return;

    window.history.replaceState(null, "", window.location.pathname);
    void open(invited);
  }, [open]);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      try {
        const listed = await matchesApi.mine();
        if (!cancelled) setMine(listed.matches);
      } catch {
        if (!cancelled) setMine([]);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  // Пока комната на экране, таблица подтягивается сама: иначе не видно, что
  // остальные уже доиграли
  const openCode = room?.code ?? null;

  useEffect(() => {
    if (openCode === null) return undefined;

    const timer = window.setInterval(() => {
      void (async () => {
        try {
          setRoom(await matchesApi.get(openCode));
        } catch {
          // Сеть моргнула — покажем то, что уже есть, и попробуем позже
        }
      })();
    }, REFRESH_MS);

    return () => {
      window.clearInterval(timer);
    };
  }, [openCode]);

  const create = async () => {
    setBusy(true);
    try {
      setRoom(await matchesApi.create(options));
    } catch (error) {
      onError(errorMessage(error, text.room.createFailed));
    } finally {
      setBusy(false);
    }
  };

  const play = async (current: MatchView) => {
    // Своя партия в комнате продолжается, а не начинается заново: бросать
    // ради неё нечего
    if (current.my_session === null && !mayStart()) return;

    setBusy(true);
    try {
      // Второй вход в комнату сервер не примет: начатую партию продолжаем
      onJoined(
        current.my_session === null
          ? await matchesApi.join(current.code)
          : await gameApi.session(current.my_session.id),
      );
    } catch (error) {
      onError(errorMessage(error, text.room.enterFailed));
    } finally {
      setBusy(false);
    }
  };

  const closeSignups = async (wanted: string) => {
    setBusy(true);
    try {
      setRoom(await matchesApi.close(wanted));
    } catch (error) {
      onError(errorMessage(error, text.room.closeFailed));
    } finally {
      setBusy(false);
    }
  };

  if (room === null) {
    return (
      <section>
        <CardTitle>{text.room.title}</CardTitle>
        <CardSubtitle>{text.room.subtitle}</CardSubtitle>

        <p className={styles.summary}>
          {text.room.fromSolo} {summary}
          <button type="button" className={styles.edit} onClick={onEditSetup}>
            {text.room.editSetup}
          </button>
        </p>

        <Button
          variant="primary"
          block
          disabled={busy}
          onClick={() => {
            void create();
          }}
        >
          {text.room.create}
        </Button>

        <form
          className={styles.joinForm}
          onSubmit={(event) => {
            event.preventDefault();
            void open(code);
          }}
        >
          <input
            className={styles.codeInput}
            value={code}
            onChange={(event) => {
              setCode(normalizeCode(event.target.value));
            }}
            placeholder={text.room.codePlaceholder}
            aria-label={text.room.codeLabel}
            inputMode="text"
            autoComplete="off"
            maxLength={CODE_LENGTH}
          />
          <Button type="submit" disabled={busy || !isCompleteCode(code)}>
            {text.room.enter}
          </Button>
        </form>

        {mine.length > 0 && (
          <div className={styles.recent}>
            <span className={styles.recentLabel}>{text.room.mine}</span>
            <div className={styles.recentList}>
              {mine.map((entry) => (
                <button
                  key={entry.code}
                  type="button"
                  className={styles.recentItem}
                  disabled={busy}
                  onClick={() => {
                    void open(entry.code);
                  }}
                >
                  <span className={styles.recentCode}>{entry.code}</span>
                  <span className={styles.recentPlayers}>{text.room.players(entry.players)}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </section>
    );
  }

  const isOpen = room.status === "open";
  const played = room.my_session !== null;
  const finished = room.my_session?.status === "finished";

  return (
    <section>
      <div className={styles.header}>
        <CardTitle>{text.room.title}</CardTitle>
        <button
          type="button"
          className={styles.leave}
          onClick={() => {
            setRoom(null);
            setCode("");
          }}
        >
          {text.room.leave}
        </button>
      </div>

      <p className={styles.code}>{room.code}</p>

      <p className={styles.meta}>
        {text.room.meta(
          room.rounds_total,
          formats.timeLimit(room.time_limit_seconds),
          room.host_name,
        )}
        {isOpen ? "" : text.room.closed}
      </p>

      <Button
        variant="ghost"
        block
        onClick={() => {
          link.share(roomLink(room.code, window.location.origin, window.location.pathname));
        }}
      >
        {linkLabel(link.state, text)}
      </Button>

      {room.standings.length === 0 ? (
        <p className={styles.empty}>{text.room.nobodyYet}</p>
      ) : (
        <div className={styles.table}>
          {room.standings.map((entry) => (
            <PlayerRow
              key={`${String(entry.rank)}-${entry.display_name}`}
              rank={entry.rank}
              avatar={entry.avatar}
              name={entry.display_name}
              // Пока игрок не дошёл до конца, вместо очков — сколько раундов
              // сыграно: иначе лидером выглядел бы тот, кто просто быстрее
              value={
                entry.is_finished
                  ? formats.number(entry.total_score)
                  : `${String(entry.rounds_done)}/${String(room.rounds_total)}`
              }
              mine={entry.is_you}
            />
          ))}
        </div>
      )}

      <div className={styles.actions}>
        {!played && isOpen && (
          <Button
            variant="primary"
            block
            disabled={busy}
            onClick={() => {
              void play(room);
            }}
          >
            {text.room.play}
          </Button>
        )}

        {!played && !isOpen && <p className={styles.empty}>{text.room.signupsClosed}</p>}

        {played && !finished && (
          <Button
            variant="primary"
            block
            disabled={busy}
            onClick={() => {
              void play(room);
            }}
          >
            {text.room.resume}
          </Button>
        )}

        {finished && room.my_session !== null && (
          <div className={styles.myScore}>
            <span className={styles.myScoreLabel}>{text.room.myScore}</span>
            <span className={styles.myScoreValue}>
              {formats.number(room.my_session.total_score)}
            </span>
          </div>
        )}

        {room.is_host && isOpen && (
          <Button
            block
            disabled={busy}
            onClick={() => {
              void closeSignups(room.code);
            }}
          >
            {text.room.closeSignups}
          </Button>
        )}
      </div>
    </section>
  );
}
