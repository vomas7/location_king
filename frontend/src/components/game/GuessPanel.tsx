/** Панель с картой мира, на которой игрок ставит точку. */

import { useEffect, useRef, useState } from "react";

import type { Answer, RoundView } from "~/api/types";
import styles from "~/components/game/GameScreen.module.css";
import { Button } from "~/components/ui/Button";
import { createGuessMap, type GuessMap } from "~/map/guess";

/** Что просят сделать и что уже сделано. */
function promptFor(answer: Answer | null, byCountry: boolean, countriesReady: boolean): string {
  if (!byCountry) {
    return answer === null ? "Отметь место на карте мира" : "Точка поставлена";
  }

  if (!countriesReady) return "Загружаем страны…";
  if (answer !== null && answer.kind === "country") return answer.name;

  return "Выбери страну, из которой снимок";
}

interface GuessPanelProps {
  round: RoundView;
  guess: Answer | null;
  busy: boolean;
  pinned: boolean;
  /** Раскрыта ли карта: пальцем её раскрывают нажатием, мышью — наведением. */
  open: boolean;
  onPin: (pinned: boolean) => void;
  onPick: (guess: Answer) => void;
  onSubmit: () => void;
}

export function GuessPanel({
  round,
  guess,
  busy,
  pinned,
  open,
  onPin,
  onPick,
  onSubmit,
}: GuessPanelProps) {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<GuessMap | null>(null);
  const onPickRef = useRef(onPick);
  onPickRef.current = onPick;

  const [ready, setReady] = useState(false);
  const [countriesReady, setCountriesReady] = useState(false);

  const byCountry = round.answer_mode === "country";

  // Карта мира одна на всю партию: пересоздавать её на каждый раунд незачем.
  // Режим при этом за партию не меняется — раунд не превращается из обычного
  // в раунд про страны, — но в зависимостях он стоит честно
  useEffect(() => {
    const element = container.current;
    if (element === null) return;

    const map = createGuessMap(element, {
      byCountry,
      onPick: (answer) => {
        onPickRef.current(answer);
      },
      onCountriesReady: setCountriesReady,
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
  }, [byCountry]);

  useEffect(() => {
    if (ready) instance.current?.clear();
  }, [round.id, ready]);

  return (
    <div
      className={[styles.panel, pinned ? styles.panelPinned : "", open ? "" : styles.panelCompact]
        .filter(Boolean)
        .join(" ")}
    >
      {/* Свёрнутой панелью на телефоне управляет большая кнопка снизу:
          вторая кнопка рядом с ней только мешала бы. Раскрытая карта
          сворачивается подписанной кнопкой, а не голой стрелкой: угадывать,
          что делает «▾», игрок не должен */}
      {open && (
        <button
          type="button"
          className={`${styles.glass} ${styles.pin}`}
          aria-pressed={pinned}
          onClick={() => {
            onPin(!pinned);
          }}
        >
          <span aria-hidden="true">{pinned ? "▾" : "▴"}</span>
          {pinned ? "Свернуть" : "Закрепить"}
        </button>
      )}

      <div className={styles.map} ref={container} />

      <div className={styles.actions}>
        {open ? (
          <>
            <p className={styles.hint}>{promptFor(guess, byCountry, countriesReady)}</p>
            <Button variant="primary" block disabled={guess === null || busy} onClick={onSubmit}>
              Ответить
            </Button>
          </>
        ) : (
          // Свёрнутая панель — это одна кнопка, и ширину ей задаёт
          // собственная надпись: на телефоне она стоит в углу под большим
          // пальцем, а не полосой во всю ширину поверх снимка
          <Button
            variant="primary"
            onClick={() => {
              onPin(true);
            }}
          >
            {guess === null
              ? byCountry
                ? "Выбрать страну"
                : "Открыть карту"
              : byCountry && guess.kind === "country"
                ? guess.name
                : "Изменить точку"}
          </Button>
        )}
      </div>
    </div>
  );
}
