/**
 * Строка игрока в таблице.
 *
 * Одна и та же в таблице лидеров, в челлендже дня и в комнате: место,
 * аватарка, имя и одно число справа. Различалось у них только это число —
 * ради него три одинаковые разметки и три одинаковых набора стилей не нужны.
 */

import type { AvatarView } from "~/api/types";
import { Avatar } from "~/components/ui/Avatar";
import styles from "~/components/ui/ui.module.css";

interface PlayerRowProps {
  rank: number;
  avatar: AvatarView;
  name: string;
  /** Что справа: очки, промах или сыгранные раунды — у каждой таблицы своё. */
  value: string;
  /** Строка самого игрока: её подсвечиваем. */
  mine?: boolean;
  /** Отмечать ли первую тройку. В комнате мест нет, там просто порядок входа. */
  medals?: boolean;
}

export function PlayerRow({
  rank,
  avatar,
  name,
  value,
  mine = false,
  medals = false,
}: PlayerRowProps) {
  return (
    <div className={[styles.playerRow, mine ? styles.playerRowMine : ""].filter(Boolean).join(" ")}>
      <span
        className={[styles.playerRank, medals && rank <= 3 ? styles.playerRankTop : ""]
          .filter(Boolean)
          .join(" ")}
      >
        {rank}
      </span>

      <Avatar avatar={avatar} size={24} name={name} />

      <span className={styles.playerName}>{name}</span>
      <span className={styles.playerValue}>{value}</span>
    </div>
  );
}
