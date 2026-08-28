/**
 * Поиск соперника.
 *
 * Условия дуэли решает сервер и он же их называет: пересказывать их здесь
 * своими словами означало бы однажды разойтись с правдой.
 */

import { useEffect, useState } from "react";

import { duels as duelsApi } from "~/api/endpoints";
import type { DuelFormat, SessionState } from "~/api/types";
import styles from "~/components/home/DuelSearch.module.css";
import { Button } from "~/components/ui/Button";
import { Card, CardSubtitle, CardTitle } from "~/components/ui/Card";
import { formatNumber, formatTimeLimit, plural } from "~/domain/format";
import { useAuth } from "~/state/authContext";
import { useDuelSearch } from "~/state/useDuelSearch";

interface DuelSearchProps {
  onJoined: (session: SessionState) => void;
  onError: (message: string) => void;
}

function searchingText(searching: number, mine: boolean): string {
  if (searching === 0) return "Сейчас никто не ищет";

  const others = mine ? searching - 1 : searching;
  if (others === 0) return "Пока ищешь только ты";

  return `${String(others)} ${plural(others, "игрок ищет", "игрока ищут", "игроков ищут")} соперника`;
}

export function DuelSearch({ onJoined, onError }: DuelSearchProps) {
  const { user } = useAuth();
  const { phase, searching, error, start, stop } = useDuelSearch(onJoined);
  const [format, setFormat] = useState<DuelFormat | null>(null);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      try {
        const loaded = await duelsApi.format();
        if (!cancelled) setFormat(loaded);
      } catch {
        // Условия — подпись под кнопкой. Не приехали — играть это не мешает
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (error !== null) onError(error);
  }, [error, onError]);

  const rules =
    format === null
      ? "Одни и те же раунды у обоих"
      : `${String(format.rounds_total)} ${plural(format.rounds_total, "раунд", "раунда", "раундов")} · ${formatTimeLimit(format.time_limit_seconds)} на раунд · одни и те же места у обоих`;

  return (
    <Card>
      <CardTitle>Дуэль</CardTitle>
      <CardSubtitle>Соперник подбирается по рейтингу</CardSubtitle>

      <div className={styles.rating}>
        <span className={styles.value}>{formatNumber(user?.rating ?? 0)}</span>
        <span className={styles.label}>
          твой рейтинг
          {user !== null && user.duels_played === 0 && " · дуэлей ещё не было"}
        </span>
      </div>

      <p className={styles.rules}>{rules}</p>

      {phase === "idle" ? (
        <Button variant="primary" size="large" block onClick={start}>
          Найти соперника
        </Button>
      ) : (
        <Button variant="ghost" size="large" block onClick={stop} disabled={phase === "joining"}>
          {phase === "joining" ? "Соперник найден…" : "Отменить поиск"}
        </Button>
      )}

      <p className={styles.queue} aria-live="polite">
        {phase === "searching" && <span className={styles.pulse} aria-hidden="true" />}
        {searchingText(searching, phase !== "idle")}
      </p>
    </Card>
  );
}
