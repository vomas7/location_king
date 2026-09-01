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
import type { Dictionary } from "~/i18n/dictionary";
import styles from "~/components/home/DuelSearch.module.css";
import { Button } from "~/components/ui/Button";
import { CardSubtitle, CardTitle } from "~/components/ui/Card";
import { useAuth } from "~/state/authContext";
import type { DuelPhase, DuelSearchController } from "~/state/useDuelSearch";
import { useFormats, useText } from "~/state/languageContext";

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
function queueText(phase: DuelPhase, text: Dictionary): string {
  if (phase === "searching") return text.duel.lookingFor;
  if (phase === "joining") return text.duel.found;

  return "";
}

export function DuelSearch({ search, mayStart }: DuelSearchProps) {
  const formats = useFormats();
  const text = useText();
  const { duel } = text;
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
      ? duel.rulesUnknown
      : duel.rules(format.rounds_total, formats.timeLimit(format.time_limit_seconds));

  return (
    <section>
      <CardTitle>{duel.title}</CardTitle>
      <CardSubtitle>{duel.subtitle}</CardSubtitle>

      <div className={styles.rating}>
        <span className={styles.value}>{formats.number(user?.rating ?? 0)}</span>
        <span className={styles.label}>
          {duel.yourRating}
          {user !== null && user.duels_played === 0 && duel.noDuelsYet}
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
          {duel.find}
        </Button>
      ) : (
        <Button
          variant="ghost"
          size="large"
          block
          onClick={search.stop}
          disabled={search.phase === "joining"}
        >
          {search.phase === "joining" ? duel.joining : duel.cancel}
        </Button>
      )}

      <p className={styles.queue} aria-live="polite">
        {search.phase === "searching" && <span className={styles.pulse} aria-hidden="true" />}
        {queueText(search.phase, text)}
      </p>
    </section>
  );
}
