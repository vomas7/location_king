/**
 * Поиск соперника.
 *
 * Сам поиск живёт выше, в меню: очередь не должна обрываться от того, что
 * игрок переключился на таблицу лидеров. Здесь только рейтинг, условия и
 * кнопка.
 *
 * Условия дуэли решает сервер и он же их называет: пересказывать их здесь
 * своими словами означало бы однажды разойтись с правдой.
 */

import { useEffect, useState } from "react";

import { duels as duelsApi } from "~/api/endpoints";
import type { DuelFormat } from "~/api/types";
import styles from "~/components/home/DuelSearch.module.css";
import { Button } from "~/components/ui/Button";
import { CardSubtitle, CardTitle } from "~/components/ui/Card";
import { formatNumber, formatTimeLimit, plural } from "~/domain/format";
import { useAuth } from "~/state/authContext";
import type { DuelPhase, DuelSearchController } from "~/state/useDuelSearch";

interface DuelSearchProps {
  search: DuelSearchController;
}

/**
 * Строка под кнопкой говорит про сам поиск, а не про очередь: сколько человек
 * в ней стоит, написано на плитке режима прямо над панелью, и повторять это
 * дважды на одном экране незачем.
 */
const QUEUE_TEXTS: Record<DuelPhase, string> = {
  idle: "",
  searching: "Ищем соперника",
  joining: "Соперник найден",
};

export function DuelSearch({ search }: DuelSearchProps) {
  const { user } = useAuth();
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

  const rules =
    format === null
      ? "Одни и те же раунды у обоих"
      : `${String(format.rounds_total)} ${plural(format.rounds_total, "раунд", "раунда", "раундов")} · ${formatTimeLimit(format.time_limit_seconds)} на раунд · одни и те же места у обоих`;

  return (
    <section>
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

      {search.phase === "idle" ? (
        <Button variant="primary" size="large" block onClick={search.start}>
          Найти соперника
        </Button>
      ) : (
        <Button
          variant="ghost"
          size="large"
          block
          onClick={search.stop}
          disabled={search.phase === "joining"}
        >
          {search.phase === "joining" ? "Соперник найден…" : "Отменить поиск"}
        </Button>
      )}

      <p className={styles.queue} aria-live="polite">
        {search.phase === "searching" && <span className={styles.pulse} aria-hidden="true" />}
        {QUEUE_TEXTS[search.phase]}
      </p>
    </section>
  );
}
