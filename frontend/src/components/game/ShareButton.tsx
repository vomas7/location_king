/** Кнопка «поделиться»: системное окно, если оно есть, иначе буфер обмена. */

import { useState } from "react";

import type { RoundResult, SessionView } from "~/api/types";
import { Button } from "~/components/ui/Button";
import { buildShareText } from "~/domain/share";

interface ShareButtonProps {
  session: SessionView;
  results: RoundResult[];
  challengeDay?: string;
}

type State = "idle" | "copied" | "failed";

const LABELS: Record<State, string> = {
  idle: "Поделиться результатом",
  copied: "Скопировано в буфер",
  failed: "Не получилось скопировать",
};

export function ShareButton({ session, results, challengeDay }: ShareButtonProps) {
  const [state, setState] = useState<State>("idle");

  const handleShare = async () => {
    const text = buildShareText({
      session,
      results,
      ...(challengeDay === undefined ? {} : { challengeDay }),
      url: window.location.origin,
    });

    // Системное окно есть на телефонах и в части десктопных браузеров
    if (typeof navigator.share === "function") {
      try {
        await navigator.share({ text });
        return;
      } catch {
        // Игрок закрыл окно или браузер отказал — пробуем буфер
      }
    }

    try {
      await navigator.clipboard.writeText(text);
      setState("copied");
    } catch {
      setState("failed");
    }

    window.setTimeout(() => {
      setState("idle");
    }, 3000);
  };

  return (
    <Button
      variant="ghost"
      block
      onClick={() => {
        void handleShare();
      }}
    >
      {LABELS[state]}
    </Button>
  );
}
