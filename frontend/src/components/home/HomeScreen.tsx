/** Главный экран: настройка партии, статистика, таблица лидеров и история. */

import { useEffect, useState } from "react";

import { game, zones } from "~/api/endpoints";
import type { SessionState, StartSessionOptions } from "~/api/types";
import { DailyChallenge } from "~/components/home/DailyChallenge";
import { DeleteAccount } from "~/components/home/DeleteAccount";
import { GameHistory } from "~/components/home/GameHistory";
import styles from "~/components/home/HomeScreen.module.css";
import { Leaderboard } from "~/components/home/Leaderboard";
import { MatchRoom } from "~/components/home/MatchRoom";
import { Alert } from "~/components/ui/Alert";
import { Button } from "~/components/ui/Button";
import { Card, CardSubtitle, CardTitle } from "~/components/ui/Card";
import { Segmented } from "~/components/ui/Segmented";
import { formatDistance, formatNumber, formatTimeLimit } from "~/domain/format";
import { useAuth } from "~/state/authContext";

const ROUNDS = [3, 5, 10].map((value) => ({ value, label: String(value) }));

/**
 * Сколько земли попадает в кадр. Пять километров плотного города — это одна
 * текстура кварталов без ориентиров, поэтому лестница начинается там, где
 * в кадр уже попадает река, шоссе или берег.
 */
const EXTENTS = [
  { value: 5, label: "5 км" },
  { value: 15, label: "15 км" },
  { value: 40, label: "40 км" },
  { value: 100, label: "100 км" },
];

const TIME_LIMITS = [null, 120, 60, 30].map((value) => ({
  value,
  label: formatTimeLimit(value),
}));

/**
 * Части света. Список фиксирован: он должен совпадать с тем, что понимает
 * сервер, и не зависеть от того, какие зоны сейчас загружены.
 */
const CONTINENTS = [
  { value: null, label: "Весь мир" },
  { value: "europe", label: "Европа" },
  { value: "asia", label: "Азия" },
  { value: "africa", label: "Африка" },
  { value: "north_america", label: "Сев. Америка" },
  { value: "south_america", label: "Юж. Америка" },
  { value: "oceania", label: "Океания" },
];

const DIFFICULTIES = [
  { value: null, label: "Любая" },
  ...[1, 2, 3, 4, 5].map((value) => ({ value, label: String(value) })),
];

interface HomeScreenProps {
  error: string | null;
  onStart: (options: StartSessionOptions) => void;
  onResume: (session: SessionState) => void;
  onError: (message: string) => void;
  /** Меняется после каждой партии, чтобы таблица и история перечитались. */
  refreshKey: number;
}

export function HomeScreen({ error, onStart, onResume, onError, refreshKey }: HomeScreenProps) {
  const { user } = useAuth();

  const [rounds, setRounds] = useState(5);
  const [extent, setExtent] = useState(15);
  const [difficulty, setDifficulty] = useState<number | null>(null);
  const [timeLimit, setTimeLimit] = useState<number | null>(null);
  const [continent, setContinent] = useState<string | null>(null);
  const [zoneCount, setZoneCount] = useState<number | null>(null);
  const [unfinished, setUnfinished] = useState<SessionState | null>(null);

  // Сколько зон под выбранными фильтрами: без этого игрок не понимает, почему
  // «Начать» отвечает, что зон нет
  useEffect(() => {
    let cancelled = false;

    const query = new URLSearchParams();
    if (continent !== null) query.set("continent", continent);
    if (difficulty !== null) query.set("difficulty", String(difficulty));

    void (async () => {
      try {
        const found = await zones.list(query.toString());
        if (!cancelled) setZoneCount(found.length);
      } catch {
        if (!cancelled) setZoneCount(null);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [continent, difficulty]);

  // Незавершённая партия — предлагаем продолжить, а не начинать заново
  useEffect(() => {
    let cancelled = false;

    void (async () => {
      try {
        const current = await game.current();
        const canResume = current !== null && current.current_round !== null;
        if (!cancelled) setUnfinished(canResume ? current : null);
      } catch {
        if (!cancelled) setUnfinished(null);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  if (user === null) return null;

  return (
    <div className={styles.screen}>
      <div className={styles.column}>
        {unfinished !== null && (
          <div className={styles.resume}>
            <div>
              <p className={styles.resumeText}>У тебя есть незаконченная партия</p>
              <p className={styles.resumeHint}>
                Раунд {unfinished.session.rounds_done + 1} из {unfinished.session.rounds_total}
              </p>
            </div>
            <Button
              variant="primary"
              onClick={() => {
                onResume(unfinished);
              }}
            >
              Продолжить
            </Button>
          </div>
        )}

        <Card>
          <CardTitle>Новая партия</CardTitle>
          <CardSubtitle>Настрой сложность и жми «Начать»</CardSubtitle>

          <div className={styles.options}>
            <Segmented label="Раундов" options={ROUNDS} value={rounds} onChange={setRounds} />
            <Segmented
              label="Размер участка"
              options={EXTENTS}
              value={extent}
              onChange={setExtent}
              hint="Чем меньше участок, тем труднее узнать место"
            />
            <Segmented
              label="Сложность зон"
              options={DIFFICULTIES}
              value={difficulty}
              onChange={setDifficulty}
            />
            <Segmented
              label="Часть света"
              options={CONTINENTS}
              value={continent}
              onChange={setContinent}
              {...(zoneCount === null
                ? {}
                : {
                    hint: `Подходящих зон: ${String(zoneCount)}`,
                  })}
            />
            <Segmented
              label="Время на раунд"
              options={TIME_LIMITS}
              value={timeLimit}
              onChange={setTimeLimit}
              hint="Чем быстрее ответ, тем больше очков за раунд"
            />
          </div>

          <Alert message={error} />

          <Button
            variant="primary"
            size="large"
            block
            disabled={zoneCount === 0}
            onClick={() => {
              onStart({
                rounds_total: rounds,
                view_extent_km: extent,
                difficulty,
                continent,
                time_limit_seconds: timeLimit,
              });
            }}
          >
            Начать игру
          </Button>
        </Card>

        <Card>
          <GameHistory refreshKey={refreshKey} />
        </Card>
      </div>

      <div className={styles.column}>
        <DailyChallenge refreshKey={refreshKey} onStarted={onResume} onError={onError} />

        <MatchRoom
          options={{
            rounds_total: rounds,
            view_extent_km: extent,
            difficulty,
            continent,
            time_limit_seconds: timeLimit,
          }}
          refreshKey={refreshKey}
          onJoined={onResume}
          onError={onError}
        />

        <Card>
          <CardTitle>Твоя статистика</CardTitle>

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
          </dl>

          <DeleteAccount />
        </Card>

        <Card>
          <Leaderboard refreshKey={refreshKey} />
        </Card>
      </div>
    </div>
  );
}
