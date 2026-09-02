/**
 * Конец знакомства: что человек только что попробовал и что даёт учётная
 * запись.
 *
 * Плюсы названы через то, что уже случилось: гость играл на пяти местах и
 * тремя способами, поэтому «297 мест» и «челлендж дня» здесь не обещания, а
 * продолжение того, что он видел. Обещать то, чего он не пробовал, пришлось
 * бы словами, и им не было бы веры.
 */

import type { RoundResult } from "~/api/types";
import styles from "~/components/demo/DemoScreen.module.css";
import { Button } from "~/components/ui/Button";
import { Card } from "~/components/ui/Card";
import { roundMark } from "~/domain/share";
import { useFormats, useText } from "~/state/languageContext";

interface DemoFinishProps {
  score: number;
  results: RoundResult[];
  onSignUp: () => void;
  onAgain: () => void;
  onLeave: () => void;
}

export function DemoFinish({ score, results, onSignUp, onAgain, onLeave }: DemoFinishProps) {
  const { demo: text } = useText();
  const formats = useFormats();

  // Те же квадратики, что и в конце настоящей партии: строка читается без
  // перехода куда бы то ни было и ничего не выдаёт тому, кто ещё не играл
  const marks = results.map((result) => roundMark(result.score, result.max_score)).join("");

  return (
    <div className={styles.finish}>
      <Card className={styles.card}>
        <div className={styles.head}>
          <h2 className={styles.title}>{text.finishTitle}</h2>
          <p className={styles.marks}>{marks}</p>
          <p className={styles.score}>{text.finishScore(formats.number(score))}</p>
        </div>

        <p className={styles.lead}>{text.finishLead}</p>

        <div className={styles.perksBlock}>
          <p className={styles.perksTitle}>{text.perksTitle}</p>
          <ul className={styles.perks}>
            {text.perks.map((perk) => (
              <li key={perk.title} className={styles.perk}>
                <h3 className={styles.perkTitle}>{perk.title}</h3>
                <p className={styles.perkText}>{perk.text}</p>
              </li>
            ))}
          </ul>
        </div>

        <div className={styles.actions}>
          <Button variant="primary" size="large" block onClick={onSignUp}>
            {text.signUp}
          </Button>
          <p className={styles.note}>{text.signUpNote}</p>

          <Button variant="ghost" block onClick={onAgain}>
            {text.again}
          </Button>
          <Button variant="ghost" block onClick={onLeave}>
            {text.leave}
          </Button>
        </div>
      </Card>
    </div>
  );
}
