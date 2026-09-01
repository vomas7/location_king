/** Последние партии игрока. */

import { useEffect, useState } from "react";

import { game } from "~/api/endpoints";
import type { SessionSummary } from "~/api/types";
import styles from "~/components/home/GameHistory.module.css";
import { CardTitle } from "~/components/ui/Card";
import { Skeleton } from "~/components/ui/Skeleton";
import type { Dictionary } from "~/i18n/dictionary";
import { useFormats, useText } from "~/state/languageContext";

/**
 * Как называется состояние партии. Сервер может прислать и то, чего словарь
 * не знает, — тогда показываем как есть: это лучше пустого места
 */
function statusLabel(status: string, text: Dictionary): string {
  const known: Record<string, string> = text.history.status;
  return known[status] ?? status;
}

export function GameHistory({ refreshKey }: { refreshKey: number }) {
  const formats = useFormats();
  const text = useText();
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
      <CardTitle>{text.history.title}</CardTitle>

      {sessions === null ? (
        <Skeleton rows={3} />
      ) : sessions.length === 0 ? (
        <p className={styles.empty}>{text.history.empty}</p>
      ) : (
        <div className={styles.history}>
          {sessions.map((session) => (
            <div key={session.id} className={styles.historyRow}>
              <span className={styles.historyDate}>{formats.date(session.started_at)}</span>
              <span className={styles.historyScore}>{formats.number(session.total_score)}</span>
              <span className={styles.historyMeta}>
                {text.history.rounds(session.rounds_done)}
                {" · "}
                {statusLabel(session.status, text)}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
