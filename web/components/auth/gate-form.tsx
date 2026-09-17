"use client";

import { useState, type FormEvent } from "react";
import { AuthCard, AuthShell } from "@/components/auth/auth-shell";
import { Button } from "@/components/ui/button";
import { Field, PasswordInput } from "@/components/ui/field";

/* The preview password, on the sign-in shell so it reads as part of the product. */
export function GateForm({ next }: { next: string }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!password) {
      setError("Type the preview password.");
      return;
    }
    setWorking(true);
    setError(null);
    try {
      const res = await fetch("/api/gate", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (res.ok) {
        window.location.assign(next);
        return;
      }
      const data = (await res.json().catch(() => ({}))) as { error?: string };
      setError(data.error ?? "That is not the password.");
    } catch {
      setError("Something went wrong. Try again.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <AuthShell
      headline="A preview of PPCWay, for the people building it."
      body="This site is not public yet. Enter the preview password to look around."
    >
      <AuthCard title="Preview password" onSubmit={submit}>
        <Field label="Password" error={error ?? undefined}>
          {(id) => (
            <PasswordInput
              id={id}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              invalid={Boolean(error)}
              autoComplete="current-password"
              autoFocus
            />
          )}
        </Field>
        <Button type="submit" full working={working ? "Checking" : false}>
          Open the preview
        </Button>
      </AuthCard>
    </AuthShell>
  );
}
