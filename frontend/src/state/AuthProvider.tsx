/** Провайдер авторизации: профиль игрока и вход. */

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { auth } from "~/api/endpoints";
import { hasSession, setTokens } from "~/api/tokens";
import type { UserProfile } from "~/api/types";
import { AuthContext, type AuthStatus } from "~/state/authContext";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [status, setStatus] = useState<AuthStatus>(hasSession() ? "loading" : "anonymous");

  // Сохранённый токен мог протухнуть: проверяем его, а не верим на слово
  useEffect(() => {
    if (!hasSession()) return;

    let cancelled = false;

    void (async () => {
      try {
        const profile = await auth.me();
        if (cancelled) return;

        setUser(profile);
        setStatus("authorized");
      } catch {
        if (cancelled) return;

        setTokens(null);
        setStatus("anonymous");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const accept = useCallback((profile: UserProfile) => {
    setUser(profile);
    setStatus("authorized");
  }, []);

  const value = useMemo(
    () => ({
      status,
      user,
      accept,

      login: async (email: string, password: string) => {
        accept(await auth.login(email, password));
      },

      register: async (email: string, password: string, displayName: string) => {
        accept(await auth.register(email, password, displayName));
      },

      logout: () => {
        setTokens(null);
        setUser(null);
        setStatus("anonymous");
      },

      refresh: async () => {
        try {
          setUser(await auth.me());
        } catch {
          // Профиль не обновился — прежние цифры лучше, чем пустой экран
        }
      },
    }),
    [status, user, accept],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
