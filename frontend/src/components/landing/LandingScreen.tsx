/**
 * Посадочная страница: что это за игра, как в неё играть и форма входа.
 *
 * Первый экран показывает игру и сразу даёт войти, ниже — как устроены
 * раунды, режимы, уровни сложности и ответы на частые вопросы. Тот же текст
 * поисковик видит в разметке JSON-LD в index.html.
 */

import { useRef } from "react";

import { AuthCard } from "~/components/auth/AuthCard";
import { MODES, QUESTIONS, STEPS } from "~/components/landing/content";
import { HeroSight } from "~/components/landing/HeroSight";
import styles from "~/components/landing/LandingScreen.module.css";
import type { LegalDocumentId } from "~/legal/documents";

interface LandingScreenProps {
  onOpenLegal: (document: LegalDocumentId) => void;
}

export function LandingScreen({ onOpenLegal }: LandingScreenProps) {
  const hero = useRef<HTMLElement>(null);

  return (
    <div className={styles.screen}>
      <section className={styles.hero} ref={hero}>
        <div className={styles.pitch}>
          <p className={styles.eyebrow}>Геогессер по спутниковым снимкам</p>

          <h1 className={styles.title}>
            Найди точку
            <br />
            на планете
          </h1>

          <p className={styles.lead}>
            Тебе показывают квадрат спутниковой съёмки — без подписей, указателей и координат. Найди
            это место на карте мира. Чем ближе к центру участка, тем больше очков.
          </p>

          <div className={styles.actions}>
            <a className={styles.cta} href="#play">
              Играть бесплатно
            </a>
            <a className={styles.secondary} href="#how">
              Как это работает
            </a>
          </div>

          <p className={styles.honest}>Без рекламы, без счётчиков и без файлов cookie. Всерьёз.</p>
        </div>

        <div className={styles.card}>
          <AuthCard onOpenLegal={onOpenLegal} />
        </div>

        <HeroSight hero={hero} />
      </section>

      <section className={styles.band} id="how">
        <h2 className={styles.bandTitle}>Как проходит раунд</h2>

        {/* Нумерация здесь по делу: это последовательность, а не три карточки */}
        <ol className={styles.steps}>
          {STEPS.map((step, index) => (
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
        <h2 className={styles.bandTitle}>Во что играть</h2>

        <div className={styles.modes}>
          {MODES.map((mode) => (
            <article key={mode.title} className={styles.mode}>
              <h3 className={styles.modeTitle}>{mode.title}</h3>
              <p className={styles.modeText}>{mode.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className={[styles.band, styles.fair].join(" ")}>
        <div>
          <p className={styles.eyebrow}>Насколько тяжело</p>
          <h2 className={styles.bandTitle}>Выбираешь сам</h2>
          <p className={styles.fairText}>
            На лёгком достаются места, которые узнают по силуэту, — Париж, Венеция, Манхэттен. На
            среднем крупные города знакомых стран: Гамбург, Казань, Сиэтл. Дальше города, о которых
            знают мало, и поля без единой вывески. На хардкоре остаются горы, пустыни и тайга: ни
            дорог, ни домов, только рельеф и цвет земли.
          </p>
        </div>

        <dl className={styles.numbers}>
          <div className={styles.number}>
            <dt>Очков за раунд</dt>
            <dd>5 000</dd>
          </div>
          <div className={styles.number}>
            <dt>Мест в игре</dt>
            {/* Число сверяется с каталогом тестом: соврать игроку легко,
                заметить это потом — нет */}
            <dd>277</dd>
          </div>
          <div className={styles.number}>
            <dt>Уровней приближения</dt>
            <dd>4</dd>
          </div>
        </dl>
      </section>

      <section className={styles.band}>
        <h2 className={styles.bandTitle}>Частые вопросы</h2>

        <dl className={styles.faq}>
          {QUESTIONS.map((item) => (
            <div key={item.question} className={styles.question}>
              <dt className={styles.questionTitle}>{item.question}</dt>
              <dd className={styles.answer}>{item.answer}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className={styles.finish}>
        <h2 className={styles.finishTitle}>Проверим, насколько ты знаешь Землю?</h2>
        <a className={styles.cta} href="#play">
          Начать игру
        </a>
      </section>
    </div>
  );
}
