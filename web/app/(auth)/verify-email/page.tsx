"use client";

import { useState, type FormEvent } from "react";
import { AuthCard, AuthShell } from "@/components/auth/auth-shell";
import { Button, TextLink } from "@/components/ui/button";
import { CodeField } from "@/components/auth/code-field";

export default function VerifyEmailPage() {
  const [working, setWorking] = useState(false);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
  }
  return (
    <AuthShell
      headline="One quick check."
      body="We confirm the email is really yours before we connect it to anything that can spend money."
      footnote="Free for 14 days. Cancel from Settings any time."
      below={
        <>
          Nothing arrived? <TextLink href="#">Send another code</TextLink>
        </>
      }
    >
      <AuthCard
        title="Check your inbox"
        intro="We sent a six-digit code to dana@alphaplumbing.ca. It works for 15 minutes."
        onSubmit={submit}
      >
        <CodeField label="Code from the email" defaultValue="702 518" />
        <Button type="submit" full className="h-12" working={working && "Checking"}>
          Verify email
        </Button>
      </AuthCard>
    </AuthShell>
  );
}
