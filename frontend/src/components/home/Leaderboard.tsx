/** Таблица лидеров с переключением метрики. */

import { useEffect, useState } from "react";

import { leaderboard as leaderboardApi } from "~/api/endpoints";
import type {
  Leaderboard as LeaderboardData,
  LeaderboardEntry,
  LeaderboardMetric,
} from "~/api/types";
import styles from "~/components/home/Leaderboard.module.css";
import { Avatar } from "~/components/ui/Avatar";
import { CardTitle } from "~/components/ui/Card";
import { Skeleton } from "~/components/ui/Skeleton";
import { formatDistance, formatNumber } from "~/domain/format";

const METRICS: { value: LeaderboardMetric; label: string }[] = [
  { value: "best", label: "Партия" },
  { value: "total", label: "Сумма" },
  { value: "accuracy", label: "Точность" },
];

/** Подпись под переключателем: что именно означает выбранная метрика. */
const CAPTIONS: Record<LeaderboardMetric, string> = {
  best: "Очков за раунд в лучшей партии",
  total: "Сумма очков за все партии",
  accuracy: "Средний промах за раунд, от пяти раундов",
};

/**
 * Отдельный зачёт на каждые условия игры.
 *
 * Общая таблица складывает несравнимое: партия на лёгком уровне и партия в
 * тайге стоят разного труда, а очки у них одни и те же. Значения ключей — те
 * же, что понимает сервер.
 */
const SCOPES: { value: string; label: string }[] = [
  { value: "", label: "Все партии" },
  { value: "among_friends=true", label: "Друзья" },
  { value: "difficulty=easy", label: "Легко" },
  { value: "difficulty=normal", label: "Средне" },
  { value: "difficulty=hard", label: "Сложно" },
  { value: "difficulty=hardcore", label: "Хардкор" },
  { value: "country_group=russia", label: "Россия" },
  { value: "country_group=usa", label: "США" },
  { value: "country_group=eu", label: "Евросоюз" },
];

function valueOf(entry: LeaderboardEntry, metric: LeaderboardMetric): string {
  if (metric === "best") return formatNumber(entry.best_score);
  if (metric === "total") return formatNumber(entry.total_score);
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
    <div className={[styles.row, isMe ? styles.rowMe : ""].filter(Boolean).join(" ")}>
      <span
        className={[styles.rank, entry.rank <= 3 ? styles.rankTop : ""].filter(Boolean).join(" ")}
      >
        {entry.rank}
      </span>
      <Avatar avatar={entry.avatar} size={24} name={entry.display_name} />
      <span className={styles.player}>{entry.display_name}</span>
      <span className={styles.value}>{valueOf(entry, metric)}</span>
    </div>
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

      <div className={styles.metrics} role="tablist" aria-label="Метрика таблицы лидеров">
        {METRICS.map((option) => (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={option.value === metric}
            className={[styles.metric, option.value === metric ? styles.metricActive : ""]
              .filter(Boolean)
              .join(" ")}
            onClick={() => {
              setMetric(option.value);
            }}
          >
            {option.label}
          </button>
        ))}
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

      <p className={styles.caption}>{CAPTIONS[metric]}</p>

      {failed && <p className={styles.empty}>Не удалось загрузить таблицу</p>}

      {!failed && data === null && <Skeleton rows={4} />}

      {!failed && data !== null && entries.length === 0 && (
        <p className={styles.empty}>
          {scope === ""
            ? "Пока никто не сыграл ни одной партии. Займи первое место"
            : "На этих условиях ещё никто не играл. Займи первое место"}
        </p>
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
