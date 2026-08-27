/** Панель с картой мира, на которой игрок ставит точку. */

import { useEffect, useRef, useState } from "react";

import styles from "~/components/game/GameScreen.module.css";
import { Button } from "~/components/ui/Button";
import { createGuessMap, type GuessMap, type LonLat } from "~/map/guess";

interface GuessPanelProps {
  /** Меняется при смене раунда: по нему сбрасывается поставленная точка. */
  roundId: number;
  guess: LonLat | null;
  busy: boolean;
  pinned: boolean;
  onPin: (pinned: boolean) => void;
  onPick: (guess: LonLat) => void;
  onSubmit: () => void;
}

export function GuessPanel({
  roundId,
  guess,
  busy,
  pinned,
  onPin,
  onPick,
  onSubmit,
}: GuessPanelProps) {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<GuessMap | null>(null);
  const onPickRef = useRef(onPick);
  onPickRef.current = onPick;

  const [ready, setReady] = useState(false);

  // Карта мира одна на всю партию: пересоздавать её на каждый раунд незачем
  useEffect(() => {
    const element = container.current;
    if (element === null) return;

    const map = createGuessMap(element, (point) => {
      onPickRef.current(point);
    });
    instance.current = map;
    setReady(true);

    // Панель меняет размер при наведении — карте нужно об этом знать
    const observer = new ResizeObserver(() => {
      map.refresh();
    });
    observer.observe(element);

    return () => {
      observer.disconnect();
      map.destroy();
      instance.current = null;
      setReady(false);
    };
  }, []);

  useEffect(() => {
    if (ready) instance.current?.clear();
  }, [roundId, ready]);

  return (
    <div className={[styles.panel, pinned ? styles.panelPinned : ""].filter(Boolean).join(" ")}>
      <button
        type="button"
        className={styles.pin}
        aria-pressed={pinned}
        title={pinned ? "Свернуть карту" : "Закрепить карту раскрытой"}
        onClick={() => {
          onPin(!pinned);
        }}
      >
        {pinned ? "▾" : "▴"}
      </button>

      <div className={styles.map} ref={container} />

      <div className={styles.actions}>
        <p className={styles.hint}>
          {guess === null ? "Кликни по карте, чтобы поставить точку" : "Точка поставлена"}
        </p>
        <Button variant="primary" block disabled={guess === null || busy} onClick={onSubmit}>
          Ответить
        </Button>
      </div>
    </div>
  );
}
