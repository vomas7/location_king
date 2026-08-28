/**
 * Челлендж дня: одна серия раундов на сутки для всех игроков.
 *
 * Состояние приходит сверху: то же самое видно на плитке режима, а запрос
 * должен быть один.
 */

import { useState } from "react";

import { errorMessage } from "~/api/client";
import { challenge as challengeApi } from "~/api/endpoints";
import type { DailyChallenge as DailyChallengeData, SessionState } from "~/api/types";
import styles from "~/components/home/DailyChallenge.module.css";
import { PlayerRow } from "~/components/ui/PlayerRow";
import { Button } from "~/components/ui/Button";
import { CardTitle } from "~/components/ui/Card";
import { Skeleton } from "~/components/ui/Skeleton";
import { formatNumber, plural } from "~/domain/format";
import { useAuth } from "~/state/authContext";

interface DailyChallengeProps {
  /** Пусто, пока состояние челленджа не приехало. */
  data: DailyChallengeData | null;
  onStarted: (session: SessionState) => void;
  onError: (message: string) => void;
}

function formatDay(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
}

export function DailyChallenge({ data, onStarted, onError }: DailyChallengeProps) {
  const { user } = useAuth();

  const [busy, setBusy] = useState(false);

  if (user === null) return null;

  // Панель занимает своё место сразу: иначе меню подпрыгивает, когда ответ
  // приходит
  if (data === null) {
    return (
      <section>
        <div className={styles.header}>
          <CardTitle>Челлендж дня</CardTitle>
        </div>
        <Skeleton rows={4} />
      </section>
    );
  }

  const played = data.my_session !== null;
  const finished = data.my_session?.status === "finished";

  const handleStart = async () => {
    setBusy(true);
    try {
      onStarted(await challengeApi.start());
    } catch (error) {
      onError(errorMessage(error, "Не удалось начать челлендж"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <div className={styles.header}>
        <CardTitle>Челлендж дня</CardTitle>
        <span className={styles.day}>{formatDay(data.day)}</span>
      </div>

      <p className={styles.subtitle}>
        {data.rounds_total} {plural(data.rounds_total, "раунд", "раунда", "раундов")} — одни и те же
        для всех. Одна попытка в сутки.
      </p>

      {data.current_streak > 0 && (
        <p className={styles.streak}>
          <strong>{data.current_streak}</strong>{" "}
          {plural(data.current_streak, "день", "дня", "дней")} подряд
          {finished ? "" : " — сыграй сегодня, чтобы не прервать"}
          {data.best_streak > data.current_streak && (
            <span className={styles.streakBest}> · рекорд {data.best_streak}</span>
          )}
        </p>
      )}

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
            <PlayerRow
              key={`${String(entry.rank)}-${entry.display_name}`}
              rank={entry.rank}
              avatar={entry.avatar}
              name={entry.display_name}
              value={formatNumber(entry.total_score)}
              mine={entry.display_name === (user.display_name ?? user.username)}
              medals
            />
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
    </section>
  );
}
