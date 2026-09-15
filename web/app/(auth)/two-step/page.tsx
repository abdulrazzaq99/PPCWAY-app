"use client";

import { useState, type FormEvent } from "react";
import { AuthCard, AuthShell } from "@/components/auth/auth-shell";
import { CodeField } from "@/components/auth/code-field";
import { Button, TextLink } from "@/components/ui/button";

export default function TwoStepPage() {
  const [working, setWorking] = useState(false);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
  }
  return (
    <AuthShell
      headline="One more step."
      body="Two-step sign-in keeps your ad spend out of the wrong hands."
      footnote="Free for 14 days. No card needed to look around."
      below={
        <>
          Lost your phone? <TextLink href="#">Use a backup code</TextLink>
        </>
      }
    >
      <AuthCard
        title="Enter your code"
        intro="Open your authenticator app and type the six-digit code for PPCWay."
        onSubmit={submit}
      >
        <CodeField label="Six-digit code" defaultValue="418 902" />
        <Button type="submit" full className="h-12" working={working && "Checking"}>
          Confirm
        </Button>
      </AuthCard>
    </AuthShell>
  );
}
