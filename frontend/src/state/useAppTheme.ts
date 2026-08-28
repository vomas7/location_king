/**
 * Оформление интерфейса.
 *
 * Своего состояния у темы нет: она свойство игрока и приезжает вместе с
 * профилем. Пока игрок не вошёл — берётся копия из браузера, ту же копию
 * читает public/theme.js до первой отрисовки.
 */

import { useEffect } from "react";

import { applyTheme, rememberTheme, storedTheme } from "~/domain/theme";
import { useAuth } from "~/state/authContext";

export function useAppTheme(): void {
  const { user } = useAuth();

  // Копия в браузере нужна до ответа сервера, поэтому обновляется сразу,
  // как только профиль стал известен
  const theme = user?.theme ?? storedTheme();

  useEffect(() => {
    if (user !== null) rememberTheme(user.theme);
  }, [user]);

  useEffect(() => applyTheme(theme), [theme]);
}
