/** Таблица лидеров с переключением метрики. */

import { useEffect, useState } from "react";

import { leaderboard as leaderboardApi } from "~/api/endpoints";
import type {
  Leaderboard as LeaderboardData,
  LeaderboardEntry,
  LeaderboardMetric,
} from "~/api/types";
import styles from "~/components/home/Leaderboard.module.css";
import type { Formats } from "~/domain/format";
import { PlayerRow } from "~/components/ui/PlayerRow";
import { CardTitle } from "~/components/ui/Card";
import { Segmented } from "~/components/ui/Segmented";
import { Skeleton } from "~/components/ui/Skeleton";
import type { Dictionary } from "~/i18n/dictionary";
import { useFormats, useText } from "~/state/languageContext";

/**
 * По чему ранжируем игроков.
 *
 * Метрика описана целиком в словаре: как называется в переключателе и что
 * значит. Здесь остаётся то, что от языка не зависит, — какое число показать
 * в строке и в каком порядке метрики стоят.
 */
const READ: Record<LeaderboardMetric, (entry: LeaderboardEntry, formats: Formats) => string> = {
  best: (entry, formats) => formats.number(entry.best_score),
  total: (entry, formats) => formats.number(entry.total_score),
  accuracy: (entry, formats) => formats.distance(entry.average_distance),
  sharp: (entry, formats) => formats.number(entry.sharp_rounds),
  games: (entry, formats) => formats.number(entry.games_played),
};

/** Порядок в переключателе: от того, что понятно всем, к тому, что поточнее. */
const METRIC_ORDER: LeaderboardMetric[] = ["best", "total", "accuracy", "sharp", "games"];

function metricChoices(text: Dictionary): { value: LeaderboardMetric; label: string }[] {
  return METRIC_ORDER.map((value) => ({ value, label: text.board.metrics[value].label }));
}

/** Зачёт среди друзей: он единственный зависит от того, кто спрашивает. */
const FRIENDS_SCOPE = "among_friends=true";

/**
 * Отдельный зачёт на каждые условия игры.
 *
 * Общая таблица складывает несравнимое: партия на лёгком уровне и партия в
 * тайге стоят разного труда, а очки у них одни и те же. Значения ключей — те
 * же, что понимает сервер, а подписи к ним лежат в словаре.
 */
const SCOPES: { value: string; name: keyof Dictionary["board"]["scopes"] }[] = [
  { value: "", name: "all" },
  { value: FRIENDS_SCOPE, name: "friends" },
  { value: "difficulty=easy", name: "easy" },
  { value: "difficulty=normal", name: "normal" },
  { value: "difficulty=hard", name: "hard" },
  { value: "difficulty=hardcore", name: "hardcore" },
  { value: "country_group=russia", name: "russia" },
  { value: "country_group=usa", name: "usa" },
  { value: "country_group=eu", name: "eu" },
];

/** Почему таблица пуста — зависит от того, какой зачёт выбран. */
function emptyText(scope: string, text: Dictionary): string {
  if (scope === "") return text.board.emptyAll;
  if (scope === FRIENDS_SCOPE) return text.board.emptyFriends;

  return text.board.emptyScope;
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
  const formats = useFormats();

  return (
    <PlayerRow
      rank={entry.rank}
      avatar={entry.avatar}
      name={entry.display_name}
      value={READ[metric](entry, formats)}
      mine={isMe}
      medals
    />
  );
}

export function Leaderboard({ refreshKey }: { refreshKey: number }) {
  const text = useText();
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
      <CardTitle>{text.board.title}</CardTitle>

      <div className={styles.metrics}>
        <Segmented
          label={text.board.metric}
          options={metricChoices(text)}
          value={metric}
          onChange={setMetric}
          hint={text.board.metrics[metric].hint}
        />
      </div>

      <label className={styles.scope}>
        <span className={styles.scopeLabel}>{text.board.scope}</span>
        <select
          className={styles.scopeSelect}
          value={scope}
          onChange={(event) => {
            setScope(event.target.value);
          }}
        >
          {SCOPES.map((option) => (
            <option key={option.value} value={option.value}>
              {text.board.scopes[option.name]}
            </option>
          ))}
        </select>
      </label>

      {failed && <p className={styles.empty}>{text.board.failed}</p>}

      {!failed && data === null && <Skeleton rows={4} />}

      {!failed && data !== null && entries.length === 0 && (
        <p className={styles.empty}>{emptyText(scope, text)}</p>
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
