/**
 * Посадочная страница: что это за игра, как в неё играть и форма входа.
 *
 * Первый экран показывает игру и сразу даёт войти, ниже — как устроены
 * раунды, режимы, откуда берётся честность и ответы на частые вопросы. Тот же
 * текст поисковик видит в разметке JSON-LD в index.html.
 */

import { AuthCard } from "~/components/auth/AuthCard";
import { MODES, QUESTIONS, STEPS } from "~/components/landing/content";
import styles from "~/components/landing/LandingScreen.module.css";
import { Reticle } from "~/components/landing/Reticle";
import type { LegalDocumentId } from "~/legal/documents";

interface LandingScreenProps {
  onOpenLegal: (document: LegalDocumentId) => void;
}

export function LandingScreen({ onOpenLegal }: LandingScreenProps) {
  return (
    <div className={styles.screen}>
      <section className={styles.hero}>
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

        <Reticle className={styles.decor} />
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
          <p className={styles.eyebrow}>Честная игра</p>
          <h2 className={styles.bandTitle}>Ответ не подсмотреть</h2>
          <p className={styles.fairText}>
            Координаты цели не покидают сервер до конца раунда: их нет ни в одном ответе API. Снимок
            приходит через прокси по внутренним номерам тайлов, так что в инструментах разработчика
            видно только их. Расстояние и очки тоже считает сервер — переписать их на своей стороне
            не выйдет.
          </p>
        </div>

        <dl className={styles.numbers}>
          <div className={styles.number}>
            <dt>Очков за раунд</dt>
            <dd>5 000</dd>
          </div>
          <div className={styles.number}>
            <dt>Игровых зон</dt>
            <dd>99</dd>
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
