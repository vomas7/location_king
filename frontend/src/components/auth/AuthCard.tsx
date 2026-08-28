/** Карточка входа и регистрации. */

import { useState, type FormEvent } from "react";

import { errorMessage } from "~/api/client";
import styles from "~/components/auth/AuthCard.module.css";
import { Alert } from "~/components/ui/Alert";
import { Button } from "~/components/ui/Button";
import { Card } from "~/components/ui/Card";
import { Checkbox } from "~/components/ui/Checkbox";
import { Field } from "~/components/ui/Field";
import type { LegalDocumentId } from "~/legal/documents";
import { useAuth } from "~/state/authContext";

type Mode = "login" | "register";

const MIN_PASSWORD_LENGTH = 8;

function describe(error: unknown): string {
  return errorMessage(error);
}

interface AuthCardProps {
  onOpenLegal: (document: LegalDocumentId) => void;
}

export function AuthCard({ onOpenLegal }: AuthCardProps) {
  const { login, register } = useAuth();

  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const switchMode = (next: Mode) => {
    setMode(next);
    setError(null);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);

    if (email.trim() === "" || password === "") {
      setError("Заполни email и пароль");
      return;
    }
    if (mode === "register" && password.length < MIN_PASSWORD_LENGTH) {
      setError(`Пароль должен быть не короче ${String(MIN_PASSWORD_LENGTH)} символов`);
      return;
    }
    if (mode === "register" && !accepted) {
      setError("Чтобы завести учётную запись, нужно принять условия");
      return;
    }

    setBusy(true);
    try {
      if (mode === "login") {
        await login(email.trim(), password);
      } else {
        await register(email.trim(), password, displayName.trim());
      }
    } catch (caught) {
      setError(describe(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className={styles.card} id="play">
      <div className={styles.tabs} role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "login"}
          className={[styles.tab, mode === "login" ? styles.tabActive : ""]
            .filter(Boolean)
            .join(" ")}
          onClick={() => {
            switchMode("login");
          }}
        >
          Вход
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "register"}
          className={[styles.tab, mode === "register" ? styles.tabActive : ""]
            .filter(Boolean)
            .join(" ")}
          onClick={() => {
            switchMode("register");
          }}
        >
          Регистрация
        </button>
      </div>

      <form className={styles.form} onSubmit={(event) => void handleSubmit(event)} noValidate>
        <Field
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={email}
          onChange={(event) => {
            setEmail(event.target.value);
          }}
        />

        <Field
          label="Пароль"
          type="password"
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          placeholder={`Не короче ${String(MIN_PASSWORD_LENGTH)} символов`}
          value={password}
          onChange={(event) => {
            setPassword(event.target.value);
          }}
        />

        {mode === "register" && (
          <Field
            label="Имя в таблице лидеров"
            hint="необязательно"
            type="text"
            autoComplete="nickname"
            placeholder="Как тебя показывать"
            value={displayName}
            onChange={(event) => {
              setDisplayName(event.target.value);
            }}
          />
        )}

        {mode === "register" && (
          <Checkbox
            checked={accepted}
            onChange={(event) => {
              setAccepted(event.target.checked);
            }}
          >
            Принимаю{" "}
            <button
              type="button"
              className={styles.link}
              onClick={() => {
                onOpenLegal("terms");
              }}
            >
              условия использования
            </button>{" "}
            и{" "}
            <button
              type="button"
              className={styles.link}
              onClick={() => {
                onOpenLegal("privacy");
              }}
            >
              политику конфиденциальности
            </button>
          </Checkbox>
        )}

        <Alert message={error} />

        <Button type="submit" variant="primary" block disabled={busy}>
          {mode === "login" ? "Войти" : "Создать аккаунт"}
        </Button>
      </form>

      <p className={styles.note}>
        {mode === "login" ? (
          <>
            Ещё нет аккаунта?{" "}
            <button
              type="button"
              className={styles.link}
              onClick={() => {
                switchMode("register");
              }}
            >
              Зарегистрируйся
            </button>
            {" — это полминуты"}
          </>
        ) : (
          "Нужны только email и пароль. Писем мы не отправляем и адрес никому не передаём"
        )}
      </p>
    </Card>
  );
}
