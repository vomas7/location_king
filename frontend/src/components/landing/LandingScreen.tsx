/**
 * Посадочная страница: что это за игра, как в неё играть и форма входа.
 *
 * Первый экран показывает игру и сразу даёт войти, ниже — как устроены
 * раунды, режимы, уровни сложности и ответы на частые вопросы. Тот же текст
 * поисковик видит в разметке JSON-LD в index.html.
 */

import { useEffect, useRef } from "react";

import { AuthCard } from "~/components/auth/AuthCard";
import { HeroSight } from "~/components/landing/HeroSight";
import { Footer } from "~/components/layout/Footer";
import { LanguageSwitch } from "~/components/layout/LanguageSwitch";
import styles from "~/components/landing/LandingScreen.module.css";
import type { LegalDocumentId } from "~/legal/documents";
import { useFormats, useText } from "~/state/languageContext";

/**
 * Числа, которые страница обещает игроку.
 *
 * Обещание легко дать и невозможно заметить, когда оно устарело: каталог
 * живёт в бэкенде, страница — здесь. Число мест сверяется с каталогом тестом
 * tests/unit/landingNumbers.test.ts, и он читает именно эту строку.
 */
const PLACES_IN_GAME = 297;
const SCORE_PER_ROUND = 5000;
const ZOOM_LEVELS = 4;

interface LandingScreenProps {
  onOpenLegal: (document: LegalDocumentId) => void;
  /** Начать знакомство с игрой без учётной записи. */
  onPlayDemo: () => void;
  /** Открыть карточку сразу на регистрации: пришли из знакомства. */
  signUpFirst?: boolean;
}

export function LandingScreen({
  onOpenLegal,
  onPlayDemo,
  signUpFirst = false,
}: LandingScreenProps) {
  const hero = useRef<HTMLElement>(null);
  const { landing, demo } = useText();
  const formats = useFormats();

  // Пришли из знакомства ради учётной записи: форма уже открыта на нужной
  // вкладке, но на телефоне она лежит ниже первого экрана — без прокрутки
  // человек упёрся бы в ту же посадочную страницу, с которой ушёл
  useEffect(() => {
    if (!signUpFirst) return;
    document.getElementById("play")?.scrollIntoView({ block: "center" });
  }, [signUpFirst]);

  return (
    <div className={styles.screen}>
      {/* Язык — первое, что нужно тому, кто пришёл и не читает по-русски:
          поэтому он наверху страницы, а не в подвале и не в профиле */}
      <div className={styles.bar}>
        <LanguageSwitch />
      </div>

      <section className={styles.hero} ref={hero}>
        <div className={styles.pitch}>
          <p className={styles.eyebrow}>{landing.eyebrow}</p>

          <h1 className={styles.title}>
            {landing.titleTop}
            <br />
            {landing.titleBottom}
          </h1>

          <p className={styles.lead}>{landing.lead}</p>

          {/* Главное действие — сыграть, а не завести учётную запись:
              форма входа стоит рядом и никуда не денется, а человек с улицы
              соглашается на неё охотнее, попробовав игру */}
          <div className={styles.actions}>
            <button type="button" className={styles.cta} onClick={onPlayDemo}>
              {demo.invite}
            </button>
            <a className={styles.secondary} href="#how">
              {landing.how}
            </a>
          </div>

          <p className={styles.tryNote}>{demo.inviteNote}</p>

          <p className={styles.honest}>{landing.honest}</p>
        </div>

        <div className={styles.card}>
          <AuthCard
            onOpenLegal={onOpenLegal}
            {...(signUpFirst ? { initialMode: "register" as const } : {})}
          />
        </div>

        <HeroSight hero={hero} />
      </section>

      <section className={styles.band} id="how">
        <h2 className={styles.bandTitle}>{landing.howTitle}</h2>

        {/* Нумерация здесь по делу: это последовательность, а не три карточки */}
        <ol className={styles.steps}>
          {landing.steps.map((step, index) => (
            <li key={step.title} className={styles.step}>
              <span className={styles.stepNumber}>{index + 1}</span>
              <div>
                <h3 className={styles.stepTitle}>{step.title}</h3>
                <p className={styles.stepText}>{step.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className={styles.band}>
        <h2 className={styles.bandTitle}>{landing.modesTitle}</h2>

        <div className={styles.modes}>
          {landing.modes.map((mode) => (
            <article key={mode.title} className={styles.mode}>
              <h3 className={styles.modeTitle}>{mode.title}</h3>
              <p className={styles.modeText}>{mode.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className={[styles.band, styles.fair].join(" ")}>
        <div>
          <p className={styles.eyebrow}>{landing.fairEyebrow}</p>
          <h2 className={styles.bandTitle}>{landing.fairTitle}</h2>
          <p className={styles.fairText}>{landing.fairText}</p>
        </div>

        <dl className={styles.numbers}>
          <div className={styles.number}>
            <dt>{landing.scorePerRound}</dt>
            <dd>{formats.number(SCORE_PER_ROUND)}</dd>
          </div>
          <div className={styles.number}>
            <dt>{landing.placesInGame}</dt>
            <dd>{formats.number(PLACES_IN_GAME)}</dd>
          </div>
          <div className={styles.number}>
            <dt>{landing.zoomLevels}</dt>
            <dd>{String(ZOOM_LEVELS)}</dd>
          </div>
        </dl>
      </section>

      <section className={styles.band}>
        <h2 className={styles.bandTitle}>{landing.faqTitle}</h2>

        <dl className={styles.faq}>
          {landing.questions.map((item) => (
            <div key={item.question} className={styles.question}>
              <dt className={styles.questionTitle}>{item.question}</dt>
              <dd className={styles.answer}>{item.answer}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className={styles.finish}>
        <h2 className={styles.finishTitle}>{landing.finishTitle}</h2>
        <a className={styles.cta} href="#play">
          {landing.finishCta}
        </a>
      </section>

      {/* Подвал внутри страницы, а не под ней: прокручивается вся страница
          целиком, и сноски видно там, где их и ищут — в самом низу. Стоя
          отдельным блоком под экраном, он занимал нижнюю полосу всегда и
          закрывал форму входа */}
      <Footer onOpen={onOpenLegal} />
    </div>
  );
}
