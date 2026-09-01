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
import { plural } from "~/domain/format";
import { useAuth } from "~/state/authContext";
import type { DuelPhase, DuelSearchController } from "~/state/useDuelSearch";
import { useFormats } from "~/state/languageContext";

interface DuelSearchProps {
  search: DuelSearchController;
  /** Спросить, можно ли бросить начатую партию ради дуэли. */
  mayStart: () => boolean;
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

export function DuelSearch({ search, mayStart }: DuelSearchProps) {
  const formats = useFormats();
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
      : `${String(format.rounds_total)} ${plural(format.rounds_total, "раунд", "раунда", "раундов")} · ${formats.timeLimit(format.time_limit_seconds)} на раунд · одни и те же места у обоих`;

  return (
    <section>
      <CardTitle>Дуэль</CardTitle>
      <CardSubtitle>Соперник подбирается по рейтингу</CardSubtitle>

      <div className={styles.rating}>
        <span className={styles.value}>{formats.number(user?.rating ?? 0)}</span>
        <span className={styles.label}>
          твой рейтинг
          {user !== null && user.duels_played === 0 && " · дуэлей ещё не было"}
        </span>
      </div>

      <p className={styles.rules}>{rules}</p>

      {search.phase === "idle" ? (
        <Button
          variant="primary"
          size="large"
          block
          onClick={() => {
            // Соперник находится сам, и партия начнётся без спроса: значит,
            // и незаконченную партию закроет тоже без спроса
            if (mayStart()) search.start();
          }}
        >
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
