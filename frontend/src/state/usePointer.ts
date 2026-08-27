/**
 * Есть ли у устройства наведение курсора.
 *
 * От этого зависит поведение карты догадки: мышью её удобно раскрывать
 * подводом курсора, а на телефоне наведения не существует вовсе — там панель
 * должна открываться нажатием, иначе не откроется никогда.
 */

import { useEffect, useState } from "react";

const QUERY = "(hover: hover) and (pointer: fine)";

function detect(): boolean {
  return window.matchMedia(QUERY).matches;
}

export function useHoverPointer(): boolean {
  const [hover, setHover] = useState(detect);

  useEffect(() => {
    const media = window.matchMedia(QUERY);

    const update = () => {
      setHover(media.matches);
    };

    // Планшет с подключённой мышью меняет ответ на лету
    media.addEventListener("change", update);
    return () => {
      media.removeEventListener("change", update);
    };
  }, []);

  return hover;
}
