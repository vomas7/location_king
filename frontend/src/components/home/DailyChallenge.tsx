/** Челлендж дня: одна серия раундов на сутки для всех игроков. */

import { useEffect, useState } from "react";

import { challenge as challengeApi } from "~/api/endpoints";
import type { DailyChallenge as DailyChallengeData, SessionState } from "~/api/types";
import styles from "~/components/home/DailyChallenge.module.css";
import { Button } from "~/components/ui/Button";
import { Card, CardTitle } from "~/components/ui/Card";
import { Skeleton } from "~/components/ui/Skeleton";
import { formatNumber, plural } from "~/domain/format";
import { useAuth } from "~/state/authContext";

interface DailyChallengeProps {
  /** Меняется после каждой партии, чтобы таблица дня перечиталась. */
  refreshKey: number;
  onStarted: (session: SessionState) => void;
  onError: (message: string) => void;
}

function formatDay(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
}

export function DailyChallenge({ refreshKey, onStarted, onError }: DailyChallengeProps) {
  const { user } = useAuth();

  const [data, setData] = useState<DailyChallengeData | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      try {
        const loaded = await challengeApi.today();
        if (!cancelled) setData(loaded);
      } catch {
        if (!cancelled) setData(null);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  if (user === null) return null;

  // Карточка занимает своё место сразу: иначе весь столбец подпрыгивает,
  // когда ответ приходит
  if (data === null) {
    return (
      <Card className={styles.card}>
        <div className={styles.header}>
          <CardTitle>Челлендж дня</CardTitle>
        </div>
        <Skeleton rows={4} />
      </Card>
    );
  }

  const played = data.my_session !== null;
  const finished = data.my_session?.status === "finished";

  const handleStart = async () => {
    setBusy(true);
    try {
      onStarted(await challengeApi.start());
    } catch (error) {
      onError(error instanceof Error ? error.message : "Не удалось начать челлендж");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className={styles.card}>
      <div className={styles.header}>
        <CardTitle>Челлендж дня</CardTitle>
        <span className={styles.day}>{formatDay(data.day)}</span>
      </div>

      <p className={styles.subtitle}>
        {data.rounds_total} {plural(data.rounds_total, "раунд", "раунда", "раундов")} — одни и те же
        для всех. Одна попытка в сутки.
      </p>

      {finished && data.my_session !== null && (
        <div className={styles.played}>
          <span className={styles.playedLabel}>Твой результат сегодня</span>
          <span className={styles.playedScore}>{formatNumber(data.my_session.total_score)}</span>
        </div>
      )}

      {data.results.length === 0 ? (
        <p className={styles.empty}>
          {finished ? "Ты пока единственный, кто сыграл" : "Сегодня ещё никто не доиграл до конца"}
        </p>
      ) : (
        <div className={styles.results}>
          {data.results.map((entry) => (
            <div
              key={`${String(entry.rank)}-${entry.display_name}`}
              className={[
                styles.row,
                entry.display_name === (user.display_name ?? user.username) ? styles.rowMe : "",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              <span
                className={[styles.rank, entry.rank <= 3 ? styles.rankTop : ""]
                  .filter(Boolean)
                  .join(" ")}
              >
                {entry.rank}
              </span>
              <span className={styles.player}>{entry.display_name}</span>
              <span className={styles.score}>{formatNumber(entry.total_score)}</span>
            </div>
          ))}
        </div>
      )}

      {!played && (
        <Button
          variant="primary"
          block
          disabled={busy}
          onClick={() => {
            void handleStart();
          }}
        >
          Играть челлендж
        </Button>
      )}

      {played && !finished && (
        <Button
          variant="ghost"
          block
          disabled={busy}
          onClick={() => {
            void handleStart();
          }}
        >
          Продолжить челлендж
        </Button>
      )}
    </Card>
  );
}
