/** Карточка входа и регистрации. */

import { useState, type FormEvent } from "react";

import { errorMessage } from "~/api/client";
import styles from "~/components/auth/AuthCard.module.css";
import { Alert } from "~/components/ui/Alert";
import { Button } from "~/components/ui/Button";
import { Card } from "~/components/ui/Card";
import { Checkbox } from "~/components/ui/Checkbox";
import { Field } from "~/components/ui/Field";
import { PasswordField } from "~/components/ui/PasswordField";
import type { LegalDocumentId } from "~/legal/documents";
import { useAuth } from "~/state/authContext";
import { useText } from "~/state/languageContext";

type Mode = "login" | "register";

const MIN_PASSWORD_LENGTH = 8;

function describe(error: unknown): string {
  return errorMessage(error);
}

interface AuthCardProps {
  onOpenLegal: (document: LegalDocumentId) => void;
  /**
   * С какой вкладки открыться. Регистрация нужна тому, кто пришёл сюда из
   * знакомства с игрой: аккаунта у него заведомо нет, и вкладка входа была бы
   * лишним нажатием.
   */
  initialMode?: Mode;
}

export function AuthCard({ onOpenLegal, initialMode = "login" }: AuthCardProps) {
  const { login, register } = useAuth();
  const { auth: text } = useText();

  const [mode, setMode] = useState<Mode>(initialMode);
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
      setError(text.fillBoth);
      return;
    }
    if (mode === "register" && password.length < MIN_PASSWORD_LENGTH) {
      setError(text.tooShort(MIN_PASSWORD_LENGTH));
      return;
    }
    if (mode === "register" && !accepted) {
      setError(text.mustAccept);
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
          {text.login}
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
          {text.register}
        </button>
      </div>

      <form className={styles.form} onSubmit={(event) => void handleSubmit(event)} noValidate>
        <Field
          label={text.email}
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={email}
          onChange={(event) => {
            setEmail(event.target.value);
          }}
        />

        <PasswordField
          label={text.password}
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          placeholder={text.passwordPlaceholder(MIN_PASSWORD_LENGTH)}
          value={password}
          onChange={(event) => {
            setPassword(event.target.value);
          }}
        />

        {mode === "register" && (
          <Field
            label={text.displayName}
            hint={text.displayNameHint}
            type="text"
            autoComplete="nickname"
            placeholder={text.displayNamePlaceholder}
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
            {text.acceptBefore}{" "}
            <button
              type="button"
              className={styles.link}
              onClick={() => {
                onOpenLegal("terms");
              }}
            >
              {text.acceptTerms}
            </button>{" "}
            {text.acceptAnd}{" "}
            <button
              type="button"
              className={styles.link}
              onClick={() => {
                onOpenLegal("privacy");
              }}
            >
              {text.acceptPrivacy}
            </button>
          </Checkbox>
        )}

        <Alert message={error} />

        <Button type="submit" variant="primary" block disabled={busy}>
          {mode === "login" ? text.submitLogin : text.submitRegister}
        </Button>
      </form>

      <p className={styles.note}>
        {mode === "login" ? (
          <>
            {text.noAccount}{" "}
            <button
              type="button"
              className={styles.link}
              onClick={() => {
                switchMode("register");
              }}
            >
              {text.goRegister}
            </button>
            {text.quick}
          </>
        ) : (
          text.onlyEmail
        )}
      </p>
    </Card>
  );
}
