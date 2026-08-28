/**
 * Профиль: как игрока видят другие, чего он добился и что с его данными.
 *
 * Правовые ссылки живут здесь, а не в подвале: подвал из меню убран — на
 * телефоне он занимал экран строками, которые открывают раз в жизни, — но
 * найти документы игрок обязан, и раздел о себе для них самое место.
 */

import { DeleteAccount } from "~/components/home/DeleteAccount";
import styles from "~/components/home/ProfilePanel.module.css";
import { PublicProfile } from "~/components/home/PublicProfile";
import { Credits, LegalLinks } from "~/components/layout/AboutLinks";
import { CardTitle } from "~/components/ui/Card";
import { formatDistance, formatNumber } from "~/domain/format";
import type { LegalDocumentId } from "~/legal/documents";
import { useAuth } from "~/state/authContext";

interface ProfilePanelProps {
  onOpenLegal: (document: LegalDocumentId) => void;
}

export function ProfilePanel({ onOpenLegal }: ProfilePanelProps) {
  const { user } = useAuth();

  if (user === null) return null;

  return (
    <section>
      <CardTitle>Профиль</CardTitle>

      <PublicProfile />

      <dl className={styles.metrics}>
        <div className={styles.metric}>
          <dt>Партий</dt>
          <dd>{formatNumber(user.games_played)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>Раундов</dt>
          <dd>{formatNumber(user.total_rounds)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>Лучшая партия</dt>
          <dd>{formatNumber(user.best_score)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>Средний промах</dt>
          <dd>{formatDistance(user.average_distance)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>Рейтинг</dt>
          <dd>{formatNumber(user.rating)}</dd>
        </div>
      </dl>

      <DeleteAccount />

      <div className={styles.about}>
        <LegalLinks onOpen={onOpenLegal} />
        <Credits />
      </div>
    </section>
  );
}
