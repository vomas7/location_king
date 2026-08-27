/**
 * Комната: та же серия раундов, но для компании.
 *
 * Комната открывается тремя путями — создали, ввели код, пришли по ссылке
 * `?room=CODE`. Дальше все три ведут себя одинаково, поэтому состояние здесь
 * одно: открытая комната либо её нет.
 */

import { useCallback, useEffect, useState } from "react";

import { game as gameApi, matches as matchesApi } from "~/api/endpoints";
import type { MatchSummary, MatchView, SessionState, StartSessionOptions } from "~/api/types";
import styles from "~/components/home/MatchRoom.module.css";
import { Button } from "~/components/ui/Button";
import { Card, CardSubtitle, CardTitle } from "~/components/ui/Card";
import { formatNumber, formatTimeLimit, plural } from "~/domain/format";
import {
  CODE_LENGTH,
  isCompleteCode,
  normalizeCode,
  roomFromSearch,
  roomLink,
} from "~/domain/room";
import { type ShareState, useShare } from "~/state/useShare";

interface MatchRoomProps {
  /** Условия из карточки «Новая партия»: комната собирается по ним же. */
  options: StartSessionOptions;
  /** Меняется после каждой партии, чтобы таблица комнаты перечиталась. */
  refreshKey: number;
  onJoined: (session: SessionState) => void;
  onError: (message: string) => void;
}

/** Как часто перечитывать таблицу, пока комната открыта. */
const REFRESH_MS = 10000;

const LINK_LABELS: Record<ShareState, string> = {
  idle: "Скопировать ссылку",
  shared: "Скопировать ссылку",
  copied: "Ссылка скопирована",
  failed: "Не получилось скопировать",
};

function errorText(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export function MatchRoom({ options, refreshKey, onJoined, onError }: MatchRoomProps) {
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
        onError(errorText(error, "Комната не найдена"));
      } finally {
        setBusy(false);
      }
    },
    [onError],
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
      onError(errorText(error, "Не удалось создать комнату"));
    } finally {
      setBusy(false);
    }
  };

  const play = async (current: MatchView) => {
    setBusy(true);
    try {
      // Второй вход в комнату сервер не примет: начатую партию продолжаем
      onJoined(
        current.my_session === null
          ? await matchesApi.join(current.code)
          : await gameApi.session(current.my_session.id),
      );
    } catch (error) {
      onError(errorText(error, "Не удалось войти в комнату"));
    } finally {
      setBusy(false);
    }
  };

  const closeSignups = async (wanted: string) => {
    setBusy(true);
    try {
      setRoom(await matchesApi.close(wanted));
    } catch (error) {
      onError(errorText(error, "Не удалось закрыть набор"));
    } finally {
      setBusy(false);
    }
  };

  if (room === null) {
    return (
      <Card>
        <CardTitle>Играть с друзьями</CardTitle>
        <CardSubtitle>
          Комната — те же раунды для всех, кто вошёл. Играете каждый в своём темпе и сравниваете
          результаты.
        </CardSubtitle>

        <Button
          variant="primary"
          block
          disabled={busy}
          onClick={() => {
            void create();
          }}
        >
          Создать комнату
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
            placeholder="КОД"
            aria-label="Код комнаты"
            inputMode="text"
            autoComplete="off"
            maxLength={CODE_LENGTH}
          />
          <Button type="submit" disabled={busy || !isCompleteCode(code)}>
            Войти
          </Button>
        </form>

        {mine.length > 0 && (
          <div className={styles.recent}>
            <span className={styles.recentLabel}>Твои комнаты</span>
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
                  <span className={styles.recentPlayers}>
                    {entry.players} {plural(entry.players, "игрок", "игрока", "игроков")}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </Card>
    );
  }

  const isOpen = room.status === "open";
  const played = room.my_session !== null;
  const finished = room.my_session?.status === "finished";

  return (
    <Card className={styles.card}>
      <div className={styles.header}>
        <CardTitle>Комната</CardTitle>
        <button
          type="button"
          className={styles.leave}
          onClick={() => {
            setRoom(null);
            setCode("");
          }}
        >
          Выйти
        </button>
      </div>

      <p className={styles.code}>{room.code}</p>

      <p className={styles.meta}>
        {room.rounds_total} {plural(room.rounds_total, "раунд", "раунда", "раундов")} ·{" "}
        {formatTimeLimit(room.time_limit_seconds)} · хост {room.host_name}
        {isOpen ? "" : " · набор закрыт"}
      </p>

      <Button
        variant="ghost"
        block
        onClick={() => {
          link.share(roomLink(room.code, window.location.origin, window.location.pathname));
        }}
      >
        {LINK_LABELS[link.state]}
      </Button>

      {room.standings.length === 0 ? (
        <p className={styles.empty}>Пока никто не вошёл. Отправь ссылку друзьям.</p>
      ) : (
        <div className={styles.table}>
          {room.standings.map((entry) => (
            <div
              key={`${String(entry.rank)}-${entry.display_name}`}
              className={[styles.row, entry.is_you ? styles.rowMe : ""].filter(Boolean).join(" ")}
            >
              <span className={styles.rank}>{entry.rank}</span>
              <span className={styles.player}>{entry.display_name}</span>
              <span className={styles.progress}>
                {entry.is_finished
                  ? formatNumber(entry.total_score)
                  : `${String(entry.rounds_done)}/${String(room.rounds_total)}`}
              </span>
            </div>
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
            Играть
          </Button>
        )}

        {!played && !isOpen && <p className={styles.empty}>Набор закрыт — войти уже нельзя.</p>}

        {played && !finished && (
          <Button
            variant="primary"
            block
            disabled={busy}
            onClick={() => {
              void play(room);
            }}
          >
            Продолжить партию
          </Button>
        )}

        {finished && room.my_session !== null && (
          <div className={styles.myScore}>
            <span className={styles.myScoreLabel}>Твой результат</span>
            <span className={styles.myScoreValue}>{formatNumber(room.my_session.total_score)}</span>
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
            Закрыть набор
          </Button>
        )}
      </div>
    </Card>
  );
}
