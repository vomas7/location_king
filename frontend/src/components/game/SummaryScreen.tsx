/** Итоги партии. */

import type { RoundResult, SessionView } from "~/api/types";
import styles from "~/components/game/SummaryScreen.module.css";
import { Button } from "~/components/ui/Button";
import { Card, Eyebrow } from "~/components/ui/Card";
import { formatDistance, formatNumber, plural } from "~/domain/format";
import { scoreRatio } from "~/domain/score";

interface SummaryScreenProps {
  session: SessionView;
  results: RoundResult[];
  /** Лучший результат игрока до этой партии — чтобы отметить рекорд. */
  previousBest: number;
  isGuest: boolean;
  onPlayAgain: () => void;
  onHome: () => void;
}

export function SummaryScreen({
  session,
  results,
  previousBest,
  isGuest,
  onPlayAgain,
  onHome,
}: SummaryScreenProps) {
  const played = results.length;
  const average = played === 0 ? 0 : Math.round(session.total_score / played);
  const isRecord = played > 0 && session.total_score > previousBest;

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
          <Button variant="ghost" block onClick={onHome}>
            В меню
          </Button>
        </div>

        {isGuest && played > 0 && (
          <p className={styles.guestNote}>
            Результат гостя в таблицу лидеров не попадает. Регистрация занимает полминуты и
            сохраняет всю статистику.
          </p>
        )}
      </Card>
    </div>
  );
}
