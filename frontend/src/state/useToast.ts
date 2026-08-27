/** Короткие сообщения поверх интерфейса. */

import { useCallback, useEffect, useRef, useState } from "react";

const VISIBLE_MS = 4000;

export function useToast(): { message: string | null; show: (text: string) => void } {
  const [message, setMessage] = useState<string | null>(null);
  const timer = useRef<number | undefined>(undefined);

  const show = useCallback((text: string) => {
    setMessage(text);

    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      setMessage(null);
    }, VISIBLE_MS);
  }, []);

  useEffect(
    () => () => {
      window.clearTimeout(timer.current);
    },
    [],
  );

  return { message, show };
}
