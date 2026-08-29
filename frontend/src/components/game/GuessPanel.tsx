/** Панель с картой мира, на которой игрок ставит точку. */

import { useEffect, useRef, useState } from "react";

import type { Answer, RoundView } from "~/api/types";
import styles from "~/components/game/GameScreen.module.css";
import { Button } from "~/components/ui/Button";
import { formatNumber } from "~/domain/format";
import { createGuessMap, type GuessMap } from "~/map/guess";
import { useHoverPointer } from "~/state/usePointer";

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
  onPin: (pinned: boolean) => void;
  onPick: (guess: Answer) => void;
  /** Взять подсказку: чем именно платит игрок, знает сервер. */
  onHint: () => void;
  onSubmit: () => void;
}

export function GuessPanel({
  round,
  guess,
  busy,
  pinned,
  onPin,
  onPick,
  onHint,
  onSubmit,
}: GuessPanelProps) {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<GuessMap | null>(null);
  const onPickRef = useRef(onPick);
  onPickRef.current = onPick;

  const [ready, setReady] = useState(false);
  const [countriesReady, setCountriesReady] = useState(false);
  const hoverPointer = useHoverPointer();

  const byCountry = round.answer_mode === "country";

  // Мышью карта раскрывается подводом курсора, пальцем — нажатием
  const open = pinned || hoverPointer;

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
        {/* Подсказка видна и в свёрнутой панели: на телефоне карта закрыта
            почти всё время раунда, а решать, платить ли за неё, нужно, глядя
            на снимок */}
        {round.hint !== null && (
          <p className={styles.revealed}>
            <span>{round.hint.label}</span>
            <strong>{round.hint.value}</strong>
          </p>
        )}

        {round.hint === null && round.hint_cost > 0 && (
          <button type="button" className={styles.hintButton} disabled={busy} onClick={onHint}>
            Подсказка
            <span>−{formatNumber(round.hint_cost)} очков</span>
          </button>
        )}

        {open ? (
          <>
            <p className={styles.hint}>{promptFor(guess, byCountry, countriesReady)}</p>
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
