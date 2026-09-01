/**
 * Аватарка игрока.
 *
 * По умолчанию рисуется здесь: сервер присылает два числа — форму узора и
 * цвет. Такая аватарка есть у каждого с первой минуты, её не нужно выбирать,
 * и картинку для неё никуда не грузят.
 *
 * Узоры сделаны в духе снимка сверху: кварталы, излучина, берег, перекрёсток,
 * изолинии, радар. Абстрактные кубики были бы из другой игры.
 *
 * Кто загрузил своё лицо, показывается им. Узор при этом остаётся запасным:
 * если картинка не загрузилась, на её месте будет он, а не пустой квадрат.
 */

import { useEffect, useState } from "react";

import { image } from "~/api/images";
import type { AvatarView } from "~/api/types";
import styles from "~/components/ui/ui.module.css";
import { useText } from "~/state/languageContext";

/** Сколько форм и цветов знает клиент. Те же числа лежат в utils/avatar.py. */
const SHAPES = 6;
const COLORS = 6;

interface AvatarProps {
  avatar: AvatarView;
  /** Сторона квадрата в пикселях. */
  size?: number;
  /** Имя игрока: уходит в подпись для чтения с экрана. */
  name?: string;
}

/** Узор внутри квадрата двадцать на двадцать. */
function pattern(shape: number, color: string) {
  switch (shape) {
    case 1: // излучина реки
      return <path d="M-2 6 C6 6 4 14 12 14 L22 14" stroke={color} strokeWidth="3" fill="none" />;
    case 2: // берег наискось
      return <path d="M-2 16 L22 4 L22 22 L-2 22 Z" fill={color} />;
    case 3: // перекрёсток
      return (
        <g stroke={color} strokeWidth="3">
          <path d="M10 -2 L10 22" />
          <path d="M-2 12 L22 12" />
        </g>
      );
    case 4: // изолинии
      return (
        <g stroke={color} strokeWidth="2" fill="none">
          <path d="M-2 14 C4 8 10 18 22 10" />
          <path d="M-2 20 C4 14 10 24 22 16" />
          <path d="M2 7 C6 4 10 9 16 5" />
        </g>
      );
    case 5: // радар
      return (
        <g stroke={color} strokeWidth="2" fill="none">
          <circle cx="10" cy="10" r="3" />
          <circle cx="10" cy="10" r="7" />
        </g>
      );
    default: // кварталы
      return (
        <g fill={color}>
          <rect x="2" y="2" width="6" height="6" rx="1" />
          <rect x="12" y="2" width="6" height="3" rx="1" />
          <rect x="2" y="12" width="3" height="6" rx="1" />
          <rect x="9" y="9" width="9" height="9" rx="1" />
        </g>
      );
  }
}

export function Avatar({ avatar, size = 32, name }: AvatarProps) {
  const text = useText();
  // Незнакомые значения не ломают строку таблицы: сервер может знать больше
  // форм, чем эта страница, — она открыта со вчерашней сборки
  const shape = avatar.shape >= 0 && avatar.shape < SHAPES ? avatar.shape : 0;
  const color = `var(--avatar-${String(avatar.color >= 0 && avatar.color < COLORS ? avatar.color : 0)})`;

  // Картинка приезжает авторизованным запросом: тег img не умеет отправлять
  // токен. Пока она едет — и если не доехала — на её месте узор, а не дыра
  const [source, setSource] = useState<string | null>(null);
  const url = avatar.image_url;

  useEffect(() => {
    if (url === null) {
      setSource(null);
      return undefined;
    }

    let cancelled = false;
    void image(url).then((loaded) => {
      if (!cancelled) setSource(loaded);
    });

    return () => {
      cancelled = true;
    };
  }, [url]);

  const label = name === undefined ? text.game.avatar : text.game.avatarOf(name);

  if (source !== null) {
    return (
      <img
        className={styles.avatar}
        src={source}
        width={size}
        height={size}
        alt={label}
        decoding="async"
      />
    );
  }

  return (
    <svg
      className={styles.avatar}
      width={size}
      height={size}
      viewBox="0 0 20 20"
      role="img"
      aria-label={label}
    >
      <rect width="20" height="20" rx="6" fill="var(--surface-3)" />
      {pattern(shape, color)}
    </svg>
  );
}
