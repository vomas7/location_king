/** Таблица лидеров с переключением метрики. */

import { useEffect, useState } from "react";

import { leaderboard as leaderboardApi } from "~/api/endpoints";
import type {
  Leaderboard as LeaderboardData,
  LeaderboardEntry,
  LeaderboardMetric,
} from "~/api/types";
import styles from "~/components/home/Leaderboard.module.css";
import { PlayerRow } from "~/components/ui/PlayerRow";
import { CardTitle } from "~/components/ui/Card";
import { Segmented } from "~/components/ui/Segmented";
import { Skeleton } from "~/components/ui/Skeleton";
import { formatDistance, formatNumber } from "~/domain/format";

const METRICS: { value: LeaderboardMetric; label: string }[] = [
  { value: "best", label: "Партия" },
  { value: "total", label: "Сумма" },
  { value: "accuracy", label: "Точность" },
  { value: "sharp", label: "Меткость" },
  { value: "games", label: "Партий" },
];

/** Подпись под переключателем: что именно означает выбранная метрика. */
const CAPTIONS: Record<LeaderboardMetric, string> = {
  best: "Очков за раунд в лучшей партии",
  total: "Сумма очков за все партии",
  accuracy: "Средний промах за раунд, от пяти раундов",
  sharp: "Раундов, взятых почти в точку",
  games: "Сколько партий доиграно до конца",
};

/**
 * Отдельный зачёт на каждые условия игры.
 *
 * Общая таблица складывает несравнимое: партия на лёгком уровне и партия в
 * тайге стоят разного труда, а очки у них одни и те же. Значения ключей — те
 * же, что понимает сервер.
 */
/** Зачёт среди друзей: он единственный зависит от того, кто спрашивает. */
const FRIENDS_SCOPE = "among_friends=true";

const SCOPES: { value: string; label: string }[] = [
  { value: "", label: "Все партии" },
  { value: FRIENDS_SCOPE, label: "Друзья" },
  { value: "difficulty=easy", label: "Легко" },
  { value: "difficulty=normal", label: "Средне" },
  { value: "difficulty=hard", label: "Сложно" },
  { value: "difficulty=hardcore", label: "Хардкор" },
  { value: "country_group=russia", label: "Россия" },
  { value: "country_group=usa", label: "США" },
  { value: "country_group=eu", label: "Евросоюз" },
];

/** Почему таблица пуста — зависит от того, какой зачёт выбран. */
function emptyText(scope: string): string {
  if (scope === "") return "Пока никто не сыграл ни одной партии. Займи первое место";
  if (scope === FRIENDS_SCOPE) return "Ни ты, ни твои друзья ещё не доиграли ни одной партии";

  return "На этих условиях ещё никто не играл. Займи первое место";
}

function valueOf(entry: LeaderboardEntry, metric: LeaderboardMetric): string {
  if (metric === "best") return formatNumber(entry.best_score);
  if (metric === "total") return formatNumber(entry.total_score);
  if (metric === "sharp") return formatNumber(entry.sharp_rounds);
  if (metric === "games") return formatNumber(entry.games_played);

  return formatDistance(entry.average_distance);
}

function Row({
  entry,
  metric,
  isMe,
}: {
  entry: LeaderboardEntry;
  metric: LeaderboardMetric;
  isMe: boolean;
}) {
  return (
    <PlayerRow
      rank={entry.rank}
      avatar={entry.avatar}
      name={entry.display_name}
      value={valueOf(entry, metric)}
      mine={isMe}
      medals
    />
  );
}

export function Leaderboard({ refreshKey }: { refreshKey: number }) {
  const [metric, setMetric] = useState<LeaderboardMetric>("best");
  const [scope, setScope] = useState("");
  const [data, setData] = useState<LeaderboardData | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      try {
        const loaded = await leaderboardApi.top(metric, 10, scope);
        if (!cancelled) {
          setData(loaded);
          setFailed(false);
        }
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [metric, scope, refreshKey]);

  const entries = data?.entries ?? [];
  const me = data?.me ?? null;
  const meIsListed = me !== null && entries.some((entry) => entry.user_id === me.user_id);

  return (
    <section>
      <CardTitle>Таблица лидеров</CardTitle>

      <div className={styles.metrics}>
        <Segmented
          label="Метрика"
          options={METRICS}
          value={metric}
          onChange={setMetric}
          hint={CAPTIONS[metric]}
        />
      </div>

      <label className={styles.scope}>
        <span className={styles.scopeLabel}>Зачёт</span>
        <select
          className={styles.scopeSelect}
          value={scope}
          onChange={(event) => {
            setScope(event.target.value);
          }}
        >
          {SCOPES.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      {failed && <p className={styles.empty}>Не удалось загрузить таблицу</p>}

      {!failed && data === null && <Skeleton rows={4} />}

      {!failed && data !== null && entries.length === 0 && (
        <p className={styles.empty}>{emptyText(scope)}</p>
      )}

      <div className={styles.table}>
        {entries.map((entry) => (
          <Row
            key={entry.user_id}
            entry={entry}
            metric={metric}
            isMe={me !== null && entry.user_id === me.user_id}
          />
        ))}

        {me !== null && !meIsListed && (
          <>
            <p className={styles.separator}>···</p>
            <Row entry={me} metric={metric} isMe />
          </>
        )}
      </div>
    </section>
  );
}
