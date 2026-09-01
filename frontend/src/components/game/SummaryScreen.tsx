/** Итоги партии. */

import { useEffect, useRef, useState } from "react";

import { leaderboard as leaderboardApi } from "~/api/endpoints";
import type { RoundResult, SessionView, StartSessionOptions } from "~/api/types";
import styles from "~/components/game/SummaryScreen.module.css";
import { ShareButton } from "~/components/game/ShareButton";
import { Button } from "~/components/ui/Button";
import { Card, Eyebrow } from "~/components/ui/Card";
import { scoreRatio } from "~/domain/score";
import { scopeLabel, scopeQuery } from "~/domain/scope";
import { createReviewMap, type ReviewMap, type ReviewRound } from "~/map/review";
import { useFormats, useText } from "~/state/languageContext";

interface SummaryScreenProps {
  session: SessionView;
  results: RoundResult[];
  /** Лучший результат игрока до этой партии — чтобы отметить рекорд. */
  previousBest: number;
  /** Заполнено, если это была партия челленджа. */
  challengeDay?: string;
  /**
   * Условия партии: по ним считается место в зачёте, и по ним же партия
   * повторяется. Пусто у продолженной и у челленджа — их не переиграть.
   */
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
  const formats = useFormats();
  const text = useText();
  const played = results.length;
  const average = played === 0 ? 0 : Math.round(session.total_score / played);
  const isRecord = played > 0 && session.total_score > previousBest;

  const [rank, setRank] = useState<number | null>(null);
  // Какой раунд разбирают. null — на карте вся партия сразу
  const [selected, setSelected] = useState<number | null>(null);

  const container = useRef<HTMLDivElement>(null);
  const review = useRef<ReviewMap | null>(null);

  useEffect(() => {
    const element = container.current;
    if (element === null || played === 0) return;

    const map = createReviewMap(element, text.game.mapCredit);
    review.current = map;

    return () => {
      map.destroy();
      review.current = null;
    };
  }, [played, text.game.mapCredit]);

  useEffect(() => {
    review.current?.show(
      results.map((item): ReviewRound => ({
        index: item.index,
        target: item.target,
        guess: item.guess,
      })),
      selected,
    );
  }, [results, selected]);

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
      {/* Разбор партии разводит экран на две колонки: карта высокая, а список
          раундов узкий, и в одном столбце они не помещаются на экран целиком */}
      <Card
        className={[styles.card, played > 0 ? styles.cardReview : ""].filter(Boolean).join(" ")}
      >
        <div className={styles.head}>
          <Eyebrow>{text.game.gameOver}</Eyebrow>

          <h2 className={styles.score}>
            {formats.number(session.total_score)}
            <small>{text.game.points}</small>
          </h2>

          <p className={styles.subtitle}>
            {played === 0
              ? text.game.nothingPlayed
              : text.game.summary(played, formats.number(average))}
          </p>

          {isRecord && <p className={styles.record}>{text.game.record}</p>}

          {rank !== null && options !== null && (
            <p className={styles.rank}>
              {text.game.placeIn(rank)} <span>{scopeLabel(options, text)}</span>
            </p>
          )}
        </div>

        {played > 0 && (
          <div className={styles.review}>
            <div className={styles.map} ref={container} />
            {selected !== null && (
              <button
                type="button"
                className={styles.wholeGame}
                onClick={() => {
                  setSelected(null);
                }}
              >
                {text.game.showWholeGame}
              </button>
            )}
          </div>
        )}

        {/* Строка списка приближает карту к своему раунду: номер на карте тот
            же, что и здесь, — иначе пять точек ни с чем не связать */}
        <ol className={styles.rounds}>
          {results.map((result) => (
            <li key={result.id}>
              <button
                type="button"
                className={[styles.round, result.index === selected ? styles.roundSelected : ""]
                  .filter(Boolean)
                  .join(" ")}
                aria-pressed={result.index === selected}
                aria-label={text.game.roundOfZone(result.index, result.zone.name)}
                onClick={() => {
                  setSelected(result.index === selected ? null : result.index);
                }}
              >
                <span className={styles.number}>{result.index}</span>
                <span className={styles.place}>{result.zone.name}</span>
                <span className={styles.distance}>{formats.distance(result.distance_km)}</span>
                <span className={styles.points}>{formats.number(result.score)}</span>
                <span className={styles.bar}>
                  <span
                    className={styles.barFill}
                    style={{
                      width: `${String(scoreRatio(result.score, result.max_score) * 100)}%`,
                    }}
                  />
                </span>
              </button>
            </li>
          ))}
        </ol>

        <div className={styles.actions}>
          <Button variant="primary" size="large" block onClick={onPlayAgain}>
            {options === null ? text.game.setUpGame : text.game.playAgain}
          </Button>
          {played > 0 && (
            <ShareButton
              session={session}
              results={results}
              {...(challengeDay === undefined ? {} : { challengeDay })}
            />
          )}
          <Button variant="ghost" block onClick={onHome}>
            {text.game.toMenu}
          </Button>
        </div>
      </Card>
    </div>
  );
}
