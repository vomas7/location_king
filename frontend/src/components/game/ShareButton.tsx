/** Кнопка «поделиться результатом». */

import type { RoundResult, SessionView } from "~/api/types";
import { Button } from "~/components/ui/Button";
import { buildShareText } from "~/domain/share";
import type { Dictionary } from "~/i18n/dictionary";
import { useFormats, useText } from "~/state/languageContext";
import { type ShareState, useShare } from "~/state/useShare";

interface ShareButtonProps {
  session: SessionView;
  results: RoundResult[];
  challengeDay?: string;
}

/** Подпись кнопки: она же говорит, что произошло после нажатия */
function label(state: ShareState, text: Dictionary): string {
  if (state === "copied") return text.game.shareCopied;
  if (state === "failed") return text.game.shareFailed;

  return text.game.share;
}

export function ShareButton({ session, results, challengeDay }: ShareButtonProps) {
  const formats = useFormats();
  const text = useText();
  const { state, share } = useShare();

  return (
    <Button
      variant="ghost"
      block
      onClick={() => {
        share(
          buildShareText({
            formats,
            text,
            session,
            results,
            ...(challengeDay === undefined ? {} : { challengeDay }),
            url: window.location.origin,
          }),
        );
      }}
    >
      {label(state, text)}
    </Button>
  );
}
