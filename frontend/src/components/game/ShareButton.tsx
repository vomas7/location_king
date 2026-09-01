/** Кнопка «поделиться результатом». */

import type { RoundResult, SessionView } from "~/api/types";
import { Button } from "~/components/ui/Button";
import { buildShareText } from "~/domain/share";
import { useFormats } from "~/state/languageContext";
import { type ShareState, useShare } from "~/state/useShare";

interface ShareButtonProps {
  session: SessionView;
  results: RoundResult[];
  challengeDay?: string;
}

const LABELS: Record<ShareState, string> = {
  idle: "Поделиться результатом",
  shared: "Поделиться результатом",
  copied: "Скопировано в буфер",
  failed: "Не получилось скопировать",
};

export function ShareButton({ session, results, challengeDay }: ShareButtonProps) {
  const formats = useFormats();
  const { state, share } = useShare();

  return (
    <Button
      variant="ghost"
      block
      onClick={() => {
        share(
          buildShareText({
            formats,
            session,
            results,
            ...(challengeDay === undefined ? {} : { challengeDay }),
            url: window.location.origin,
          }),
        );
      }}
    >
      {LABELS[state]}
    </Button>
  );
}
