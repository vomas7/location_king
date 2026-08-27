/** Панель с картой мира, на которой игрок ставит точку. */

import { useEffect, useRef, useState } from "react";

import styles from "~/components/game/GameScreen.module.css";
import { Button } from "~/components/ui/Button";
import { createGuessMap, type GuessMap, type LonLat } from "~/map/guess";
import { useHoverPointer } from "~/state/usePointer";

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
  const hoverPointer = useHoverPointer();

  // Мышью карта раскрывается подводом курсора, пальцем — нажатием
  const open = pinned || hoverPointer;

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
      {/* Свёрнутой панелью на телефоне управляет большая кнопка снизу:
          маленькая стрелка рядом с ней только мешала бы */}
      {open && (
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
      )}

      <div className={styles.map} ref={container} />

      <div className={styles.actions}>
        {open ? (
          <>
            <p className={styles.hint}>
              {guess === null ? "Отметь место на карте мира" : "Точка поставлена"}
            </p>
            <Button variant="primary" block disabled={guess === null || busy} onClick={onSubmit}>
              Ответить
            </Button>
          </>
        ) : (
          <Button
            variant="primary"
            block
            onClick={() => {
              onPin(true);
            }}
          >
            {guess === null ? "Открыть карту" : "Изменить точку"}
          </Button>
        )}
      </div>
    </div>
  );
}
