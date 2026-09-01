/**
 * Профиль: как игрока видят другие, чего он добился и что с его данными.
 *
 * Правовые ссылки живут здесь, а не в подвале: подвал из меню убран — на
 * телефоне он занимал экран строками, которые открывают раз в жизни, — но
 * найти документы игрок обязан, и раздел о себе для них самое место.
 */

import { errorMessage } from "~/api/client";
import { auth } from "~/api/endpoints";
import type { Theme } from "~/api/types";
import { DeleteAccount } from "~/components/home/DeleteAccount";
import { Feedback } from "~/components/home/Feedback";
import styles from "~/components/home/ProfilePanel.module.css";
import { PublicProfile } from "~/components/home/PublicProfile";
import { Credits, LegalLinks } from "~/components/layout/AboutLinks";
import { CardTitle } from "~/components/ui/Card";
import { Segmented } from "~/components/ui/Segmented";
import { THEMES } from "~/domain/theme";
import type { LegalDocumentId } from "~/legal/documents";
import { useAuth } from "~/state/authContext";
import { useFormats, useText } from "~/state/languageContext";

interface ProfilePanelProps {
  onOpenLegal: (document: LegalDocumentId) => void;
  onError: (message: string) => void;
}

export function ProfilePanel({ onOpenLegal, onError }: ProfilePanelProps) {
  const formats = useFormats();
  const { profile } = useText();
  const { user, accept } = useAuth();

  if (user === null) return null;

  // Тема — свойство игрока: сервер отвечает обновлённым профилем, и от него
  // же её берёт всё остальное приложение
  const chooseTheme = async (theme: Theme) => {
    try {
      accept(await auth.setTheme(theme));
    } catch (error) {
      onError(errorMessage(error, profile.themeFailed));
    }
  };

  return (
    <section>
      <CardTitle>{profile.title}</CardTitle>

      <PublicProfile />

      <dl className={styles.metrics}>
        <div className={styles.metric}>
          <dt>{profile.games}</dt>
          <dd>{formats.number(user.games_played)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>{profile.rounds}</dt>
          <dd>{formats.number(user.total_rounds)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>{profile.best}</dt>
          <dd>{formats.number(user.best_score)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>{profile.averageMiss}</dt>
          <dd>{formats.distance(user.average_distance)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>{profile.rating}</dt>
          <dd>{formats.number(user.rating)}</dd>
        </div>
      </dl>

      <div className={styles.settings}>
        <Segmented
          label={profile.theme}
          options={THEMES.map((value) => ({ value, label: profile.themes[value] }))}
          value={user.theme}
          onChange={(theme) => {
            void chooseTheme(theme);
          }}
        />
      </div>

      {/* Два тихих действия подряд: рассказать об игре и уйти из неё */}
      <div className={styles.actions}>
        <Feedback />
        <DeleteAccount />
      </div>

      <div className={styles.about}>
        <LegalLinks onOpen={onOpenLegal} />
        <Credits />
      </div>
    </section>
  );
}
