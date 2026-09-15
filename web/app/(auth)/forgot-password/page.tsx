"use client";

import { useState, type FormEvent } from "react";
import { AuthCard, AuthShell } from "@/components/auth/auth-shell";
import { Button, TextLink } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";

/* Two frames: the request, then the "Check your email" confirmation once it is sent. */
export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const [working, setWorking] = useState(false);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    window.setTimeout(() => {
      setWorking(false);
      setSent(true);
    }, 600);
  }

  if (sent) {
    return (
      <AuthShell
        headline="Nearly there."
        body="The link expires in an hour and works only once, so nobody else can use it."
        footnote="Free for 14 days. No card needed to look around."
        below={
          <>
            Nothing arrived?{" "}
            <button
              type="button"
              onClick={() => setSent(false)}
              className="text-brand hover:text-brand-dark font-semibold"
            >
              Send it again
            </button>
          </>
        }
      >
        <AuthCard
          title="Check your email"
          intro="We sent a link to dana@alphaplumbing.ca. It works once and expires in an hour."
        />
      </AuthShell>
    );
  }

  return (
    <AuthShell
      headline="Locked out. It happens."
      body="Your campaigns keep running while you sort this out. Nothing pauses, and nothing is lost."
      footnote="Free for 14 days. No card needed to look around."
      below={
        <>
          Remembered it? <TextLink href="/login">Back to sign in</TextLink>
        </>
      }
    >
      <AuthCard
        title="Reset your password"
        intro="Tell us the email you signed up with and we'll send a link to set a new one."
        onSubmit={submit}
      >
        <Field label="Email">
          {(id) => (
            <Input
              id={id}
              name="email"
              type="email"
              autoComplete="email"
              defaultValue="dana@alphaplumbing.ca"
            />
          )}
        </Field>
        <Button type="submit" full className="h-12" working={working && "Sending"}>
          Send the link
        </Button>
      </AuthCard>
    </AuthShell>
  );
}
