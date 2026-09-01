/** Последние партии игрока. */

import { useEffect, useState } from "react";

import { game } from "~/api/endpoints";
import type { SessionSummary } from "~/api/types";
import styles from "~/components/home/GameHistory.module.css";
import { CardTitle } from "~/components/ui/Card";
import { Skeleton } from "~/components/ui/Skeleton";
import { plural } from "~/domain/format";
import { useFormats } from "~/state/languageContext";

const STATUS_LABELS: Record<string, string> = {
  finished: "завершена",
  abandoned: "брошена",
  active: "не доиграна",
};

export function GameHistory({ refreshKey }: { refreshKey: number }) {
  const formats = useFormats();
  const [sessions, setSessions] = useState<SessionSummary[] | null>(null);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      try {
        const history = await game.history(5);
        if (!cancelled) setSessions(history.sessions);
      } catch {
        if (!cancelled) setSessions([]);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return (
    <section>
      <CardTitle>Последние партии</CardTitle>

      {sessions === null ? (
        <Skeleton rows={3} />
      ) : sessions.length === 0 ? (
        <p className={styles.empty}>Ты ещё не сыграл ни одной партии</p>
      ) : (
        <div className={styles.history}>
          {sessions.map((session) => (
            <div key={session.id} className={styles.historyRow}>
              <span className={styles.historyDate}>{formats.date(session.started_at)}</span>
              <span className={styles.historyScore}>{formats.number(session.total_score)}</span>
              <span className={styles.historyMeta}>
                {session.rounds_done} {plural(session.rounds_done, "раунд", "раунда", "раундов")}
                {" · "}
                {STATUS_LABELS[session.status] ?? session.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
