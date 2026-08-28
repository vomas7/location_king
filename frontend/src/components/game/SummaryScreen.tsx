/** Итоги партии. */

import { useEffect, useState } from "react";

import { leaderboard as leaderboardApi } from "~/api/endpoints";
import type { RoundResult, SessionView, StartSessionOptions } from "~/api/types";
import styles from "~/components/game/SummaryScreen.module.css";
import { ShareButton } from "~/components/game/ShareButton";
import { Button } from "~/components/ui/Button";
import { Card, Eyebrow } from "~/components/ui/Card";
import { formatDistance, formatNumber, plural } from "~/domain/format";
import { scoreRatio } from "~/domain/score";
import { scopeLabel, scopeQuery } from "~/domain/scope";

interface SummaryScreenProps {
  session: SessionView;
  results: RoundResult[];
  /** Лучший результат игрока до этой партии — чтобы отметить рекорд. */
  previousBest: number;
  /** Заполнено, если это была партия челленджа. */
  challengeDay?: string;
  /** Условия партии: по ним считается место в зачёте. Пусто у продолженной. */
  options: StartSessionOptions | null;
  onPlayAgain: () => void;
  onHome: () => void;
}

export function SummaryScreen({
  session,
  results,
  previousBest,
  challengeDay,
  options,
  onPlayAgain,
  onHome,
}: SummaryScreenProps) {
  const played = results.length;
  const average = played === 0 ? 0 : Math.round(session.total_score / played);
  const isRecord = played > 0 && session.total_score > previousBest;

  const [rank, setRank] = useState<number | null>(null);

  // Место в зачёте именно тех условий, на которых играли: иначе рекорд на
  // лёгком уровне сравнивался бы с чужим хардкором
  useEffect(() => {
    if (options === null || played === 0) return;

    let cancelled = false;

    void (async () => {
      try {
        const table = await leaderboardApi.top("best", 1, scopeQuery(options));
        if (!cancelled) setRank(table.me?.rank ?? null);
      } catch {
        // Место — приятная мелочь, а не итог партии: молча обходимся без него
        if (!cancelled) setRank(null);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [options, played]);

  return (
    <div className={styles.screen}>
      <Card className={styles.card}>
        <Eyebrow>Партия окончена</Eyebrow>

        <h2 className={styles.score}>
          {formatNumber(session.total_score)}
          <small>очков</small>
        </h2>

        <p className={styles.subtitle}>
          {played === 0
            ? "Ни одного раунда не сыграно"
            : `${String(played)} ${plural(played, "раунд", "раунда", "раундов")} · в среднем ${formatNumber(average)} за раунд`}
        </p>

        {isRecord && <p className={styles.record}>Это твой лучший результат</p>}

        {rank !== null && options !== null && (
          <p className={styles.rank}>
            <strong>{rank}</strong> место в зачёте <span>{scopeLabel(options)}</span>
          </p>
        )}

        <ol className={styles.rounds}>
          {results.map((result) => (
            <li key={result.id} className={styles.round}>
              <span className={styles.place}>{result.zone.name}</span>
              <span className={styles.distance}>{formatDistance(result.distance_km)}</span>
              <span className={styles.points}>{formatNumber(result.score)}</span>
              <span className={styles.bar}>
                <span
                  className={styles.barFill}
                  style={{ width: `${String(scoreRatio(result.score, result.max_score) * 100)}%` }}
                />
              </span>
            </li>
          ))}
        </ol>

        <div className={styles.actions}>
          <Button variant="primary" size="large" block onClick={onPlayAgain}>
            Играть снова
          </Button>
          {played > 0 && (
            <ShareButton
              session={session}
              results={results}
              {...(challengeDay === undefined ? {} : { challengeDay })}
            />
          )}
          <Button variant="ghost" block onClick={onHome}>
            В меню
          </Button>
        </div>
      </Card>
    </div>
  );
}
