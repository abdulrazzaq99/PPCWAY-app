"use client";

import { useState, type FormEvent } from "react";
import { AuthCard, AuthShell } from "@/components/auth/auth-shell";
import { Button, LinkButton, TextLink } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";

/*
  Asking for a reset link. It says the same thing whatever happens, because
  whether an address has an account is not a stranger's business — and the
  person who does own it reads the rest in their inbox.
*/
export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const [working, setWorking] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setWorking(true);
    try {
      await fetch("/api/auth/forgot", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email: String(form.get("email") ?? "") }),
      });
    } finally {
      setWorking(false);
      setSent(true);
    }
  }

  return (
    <AuthShell
      headline="Forgotten your password?"
      body="Tell us the address you signed up with and we will send a link to set a new one."
      footnote="The link works for two hours, and once only."
      below={
        <>
          Remembered it? <TextLink href="/login">Sign in</TextLink>
        </>
      }
    >
      {sent ? (
        <AuthCard title="Check your email">
          <p className="text-muted text-[15px] leading-[23px]">
            If that address has an account, a link is on its way. It works for two hours. If nothing
            arrives, look in your spam folder before trying again.
          </p>
          <LinkButton href="/login" full>
            Back to sign in
          </LinkButton>
        </AuthCard>
      ) : (
        <AuthCard title="Send me a link" onSubmit={submit}>
          <Field label="Your email">
            {(id) => (
              <Input
                id={id}
                name="email"
                type="email"
                autoComplete="email"
                required
                placeholder="dana@alphaplumbing.ca"
              />
            )}
          </Field>
          <Button type="submit" full working={working && "Sending"}>
            Send the link
          </Button>
        </AuthCard>
      )}
    </AuthShell>
  );
}
