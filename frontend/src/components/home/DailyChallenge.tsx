/**
 * Челлендж дня: одна серия раундов на сутки для всех игроков.
 *
 * Состояние приходит сверху: то же самое видно на плитке режима, а запрос
 * должен быть один.
 */

import { useState } from "react";

import { errorMessage } from "~/api/client";
import { challenge as challengeApi, game as gameApi } from "~/api/endpoints";
import type { DailyChallenge as DailyChallengeData, SessionState } from "~/api/types";
import styles from "~/components/home/DailyChallenge.module.css";
import { PlayerRow } from "~/components/ui/PlayerRow";
import { Button } from "~/components/ui/Button";
import { CardTitle } from "~/components/ui/Card";
import { Skeleton } from "~/components/ui/Skeleton";
import { dailyStage } from "~/domain/daily";
import { useAuth } from "~/state/authContext";
import { useFormats, useText } from "~/state/languageContext";

interface DailyChallengeProps {
  /** Пусто, пока состояние челленджа не приехало. */
  data: DailyChallengeData | null;
  /** Спросить, можно ли бросить начатую партию ради этой. */
  mayStart: () => boolean;
  onStarted: (session: SessionState) => void;
  onError: (message: string) => void;
}

export function DailyChallenge({ data, mayStart, onStarted, onError }: DailyChallengeProps) {
  const formats = useFormats();
  const { daily: text } = useText();
  const { user } = useAuth();

  const [busy, setBusy] = useState(false);

  if (user === null) return null;

  // Панель занимает своё место сразу: иначе меню подпрыгивает, когда ответ
  // приходит
  if (data === null) {
    return (
      <section>
        <div className={styles.header}>
          <CardTitle>{text.title}</CardTitle>
        </div>
        <Skeleton rows={4} />
      </section>
    );
  }

  const mine = data.my_session;
  const stage = dailyStage(mine);
  const finished = stage === "finished";

  /**
   * Начатую партию продолжаем запросом самой партии, а не повторным стартом:
   * попытка в сутки одна, и на второй старт сервер честно отвечает отказом.
   */
  const handleStart = async () => {
    if (stage === "fresh" && !mayStart()) return;

    setBusy(true);
    try {
      onStarted(mine === null ? await challengeApi.start() : await gameApi.session(mine.id));
    } catch (error) {
      onError(errorMessage(error, text.failed));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <div className={styles.header}>
        <CardTitle>{text.title}</CardTitle>
        <span className={styles.day}>{formats.day(data.day)}</span>
      </div>

      <p className={styles.subtitle}>{text.subtitle(data.rounds_total)}</p>

      {data.current_streak > 0 && (
        <p className={styles.streak}>
          <strong>{data.current_streak}</strong> {text.streak(data.current_streak)}
          {finished ? "" : text.keepStreak}
          {data.best_streak > data.current_streak && (
            <span className={styles.streakBest}>{text.bestStreak(data.best_streak)}</span>
          )}
        </p>
      )}

      {finished && mine !== null && (
        <div className={styles.played}>
          <span className={styles.playedLabel}>{text.myResult}</span>
          <span className={styles.playedScore}>{formats.number(mine.total_score)}</span>
        </div>
      )}

      {data.results.length === 0 ? (
        <p className={styles.empty}>{finished ? text.onlyYouPlayed : text.nobodyFinished}</p>
      ) : (
        <div className={styles.results}>
          {data.results.map((entry) => (
            <PlayerRow
              key={`${String(entry.rank)}-${entry.display_name}`}
              rank={entry.rank}
              avatar={entry.avatar}
              name={entry.display_name}
              value={formats.number(entry.total_score)}
              mine={entry.display_name === (user.display_name ?? user.username)}
              medals
            />
          ))}
        </div>
      )}

      {stage === "fresh" && (
        <Button
          variant="primary"
          block
          disabled={busy}
          onClick={() => {
            void handleStart();
          }}
        >
          {text.play}
        </Button>
      )}

      {stage === "active" && (
        <Button
          variant="primary"
          block
          disabled={busy}
          onClick={() => {
            void handleStart();
          }}
        >
          {text.resume}
        </Button>
      )}

      {stage === "lost" && <p className={styles.lost}>{text.lost}</p>}
    </section>
  );
}
