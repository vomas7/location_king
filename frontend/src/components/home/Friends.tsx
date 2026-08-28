/**
 * Друзья.
 *
 * Добавляют по короткому коду игрока, а не по имени: имена не уникальны, и по
 * чужому имени легко найти не того. Свой код игрок показывает сам, кому
 * захочет, — он же виден в этой карточке.
 */

import { useCallback, useEffect, useState } from "react";

import { errorMessage } from "~/api/client";
import { friends as friendsApi } from "~/api/endpoints";
import type { Friend } from "~/api/types";
import styles from "~/components/home/Friends.module.css";
import { Avatar } from "~/components/ui/Avatar";
import { Button } from "~/components/ui/Button";
import { Card, CardSubtitle, CardTitle } from "~/components/ui/Card";
import { Field } from "~/components/ui/Field";
import { formatNumber } from "~/domain/format";
import { CODE_LENGTH, isCompleteCode, normalizeCode } from "~/domain/codes";
import { useShare } from "~/state/useShare";

interface FriendsProps {
  onError: (message: string) => void;
}

/** Сначала входящие заявки, потом друзья, потом свои неотвеченные. */
function inOrder(list: Friend[]): Friend[] {
  const weight = (friend: Friend) => (friend.incoming ? 0 : friend.accepted ? 1 : 2);
  return [...list].sort((one, other) => weight(one) - weight(other));
}

export function Friends({ onError }: FriendsProps) {
  const [list, setList] = useState<Friend[]>([]);
  const [myCode, setMyCode] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);

  const shared = useShare();

  const reload = useCallback(async () => {
    try {
      const loaded = await friendsApi.list();
      setList(loaded.friends);
      setMyCode(loaded.my_code);
    } catch (error) {
      onError(errorMessage(error, "Не удалось прочитать список друзей"));
    }
  }, [onError]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const act = async (action: () => Promise<unknown>, fallback: string) => {
    setBusy(true);
    try {
      await action();
      await reload();
    } catch (error) {
      onError(errorMessage(error, fallback));
    } finally {
      setBusy(false);
    }
  };

  const invite = async () => {
    await act(async () => {
      await friendsApi.invite(code);
      setCode("");
    }, "Не удалось отправить заявку");
  };

  const incoming = list.filter((friend) => friend.incoming).length;

  return (
    <Card>
      <CardTitle>Друзья</CardTitle>
      <CardSubtitle>
        {incoming === 0
          ? "Добавляют по коду игрока — имя для этого не подходит"
          : `${String(incoming)} ${incoming === 1 ? "заявка ждёт" : "заявки ждут"} ответа`}
      </CardSubtitle>

      <div className={styles.mine}>
        <span className={styles.mineLabel}>Твой код</span>
        <code className={styles.code}>{myCode}</code>
        <button
          type="button"
          className={styles.copy}
          onClick={() => {
            shared.share(myCode);
          }}
        >
          {shared.state === "copied" ? "Скопирован" : "Скопировать"}
        </button>
      </div>

      <form
        className={styles.form}
        onSubmit={(event) => {
          event.preventDefault();
          void invite();
        }}
      >
        <Field
          label="Код друга"
          placeholder={"A".repeat(CODE_LENGTH)}
          value={code}
          maxLength={CODE_LENGTH}
          onChange={(event) => {
            setCode(normalizeCode(event.target.value));
          }}
        />
        <Button type="submit" variant="primary" disabled={busy || !isCompleteCode(code)}>
          Позвать
        </Button>
      </form>

      {list.length === 0 ? (
        <p className={styles.empty}>Пока никого. Обменяйся кодами — и увидишь общий зачёт.</p>
      ) : (
        <ul className={styles.list}>
          {inOrder(list).map((friend) => (
            <li key={friend.id} className={styles.row}>
              <Avatar avatar={friend.avatar} size={26} name={friend.display_name} />

              <span className={styles.name}>
                {friend.display_name}
                {!friend.accepted && (
                  <span className={styles.pending}>
                    {friend.incoming ? "зовёт тебя" : "ждёт ответа"}
                  </span>
                )}
              </span>

              <span className={styles.rating}>{formatNumber(friend.rating)}</span>

              <span className={styles.actions}>
                {friend.incoming && (
                  <button
                    type="button"
                    className={styles.accept}
                    disabled={busy}
                    onClick={() => {
                      void act(() => friendsApi.accept(friend.id), "Не удалось принять заявку");
                    }}
                  >
                    Принять
                  </button>
                )}
                <button
                  type="button"
                  className={styles.drop}
                  disabled={busy}
                  aria-label={`Убрать ${friend.display_name}`}
                  onClick={() => {
                    void act(() => friendsApi.remove(friend.id), "Не удалось убрать");
                  }}
                >
                  ✕
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
