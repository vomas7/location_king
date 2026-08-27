/**
 * Обратный отсчёт до срока, назначенного сервером.
 *
 * Часы игрока могут расходиться с серверными, поэтому считается разница до
 * момента, который прислал сервер, а не «сколько секунд прошло у меня».
 */

import { useEffect, useState } from "react";

const TICK_MS = 250;

export interface Countdown {
  /** Сколько секунд осталось. null — время не ограничено. */
  secondsLeft: number | null;
  /** Время вышло. */
  expired: boolean;
}

export function useCountdown(deadline: string | null): Countdown {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (deadline === null) return;

    setNow(Date.now());
    const timer = window.setInterval(() => {
      setNow(Date.now());
    }, TICK_MS);

    return () => {
      window.clearInterval(timer);
    };
  }, [deadline]);

  if (deadline === null) return { secondsLeft: null, expired: false };

  const left = Math.max(0, Math.ceil((new Date(deadline).getTime() - now) / 1000));
  return { secondsLeft: left, expired: left === 0 };
}
