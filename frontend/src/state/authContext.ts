/** Контекст авторизации. Провайдер — в AuthProvider.tsx. */

import { createContext, useContext } from "react";

import type { UserProfile } from "~/api/types";

export type AuthStatus = "loading" | "anonymous" | "authorized";

export interface AuthContextValue {
  status: AuthStatus;
  user: UserProfile | null;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => void;

  /** Перечитать профиль, не трогая текущий экран. */
  refresh: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);

  if (value === null) {
    throw new Error("useAuth вызван вне AuthProvider");
  }

  return value;
}
