"use client";

import { useState, type FormEvent } from "react";
import { AuthCard, AuthShell } from "@/components/auth/auth-shell";
import { Button, TextLink } from "@/components/ui/button";
import { Field, PasswordInput } from "@/components/ui/field";

export default function ResetPasswordPage() {
  const [working, setWorking] = useState(false);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
  }
  return (
    <AuthShell
      headline="Pick something new."
      body="Anyone with your password can change what you spend, so make this one count."
      footnote="Free for 14 days. No card needed to look around."
      below={
        <>
          Changed your mind? <TextLink href="/login">Back to sign in</TextLink>
        </>
      }
    >
      <AuthCard
        title="Set a new password"
        intro="Twelve characters or more, and something you don't use anywhere else."
        onSubmit={submit}
      >
        <Field label="New password">
          {(id) => (
            <PasswordInput id={id} name="password" autoComplete="new-password" minLength={12} />
          )}
        </Field>
        <Button type="submit" full className="h-12" working={working && "Saving"}>
          Save and sign in
        </Button>
      </AuthCard>
    </AuthShell>
  );
}
