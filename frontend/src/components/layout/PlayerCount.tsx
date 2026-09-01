/**
 * Сколько людей уже играет.
 *
 * Стоит в подвале, тихой строкой рядом с подписью к карте: это не обещание и
 * не реклама, а ответ на вопрос, который человек задаёт себе на незнакомом
 * сайте, — «тут вообще кто-нибудь есть». Врать таким числом нельзя, поэтому
 * оно настоящее и приходит с сервера.
 *
 * Пока число не пришло — и если не пришло вовсе, — на его месте ничего нет.
 * Подвал от этого не прыгает: строки в нём и так переносятся.
 */

import { useEffect, useState } from "react";

import { community } from "~/api/endpoints";
import styles from "~/components/layout/Footnotes.module.css";
import { useText } from "~/state/languageContext";

export function PlayerCount() {
  const { footer } = useText();
  const [players, setPlayers] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;

    void community
      .stats()
      .then((stats) => {
        if (alive) setPlayers(stats.players);
      })
      .catch(() => {
        // Счётчик не та вещь, ради которой стоит показывать ошибку: не
        // пришёл — значит, строки просто нет
      });

    return () => {
      alive = false;
    };
  }, []);

  if (players === null) return null;

  return <p className={styles.credits}>{footer.players(players)}</p>;
}
