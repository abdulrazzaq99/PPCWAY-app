"use client";

import { useState, type FormEvent } from "react";
import { AuthCard, AuthShell } from "@/components/auth/auth-shell";
import { GoogleButton } from "@/components/auth/google-button";
import { Button, TextLink } from "@/components/ui/button";
import { Field, Input, PasswordInput } from "@/components/ui/field";
import { Chip } from "@/components/ui/chip";

/* Joining a business someone else owns. The role card says what the invitee can and cannot do. */
export default function InvitePage() {
  const [working, setWorking] = useState(false);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
  }
  return (
    <AuthShell
      headline="Dana invited you to Alpha Plumbing."
      body="You will see how the ads are doing and approve the changes PPCWay suggests. Budgets, limits and billing stay with Dana."
      footnote="This invitation works until 14 September."
      below={
        <>
          Not you? <TextLink href="#">Tell Dana</TextLink>
        </>
      }
    >
      <AuthCard title="Join Alpha Plumbing" onSubmit={submit}>
        <GoogleButton />
        <p className="text-faint text-[13px] leading-4 font-medium">or use your email</p>
        <Field label="Email">
          {(id) => (
            <Input
              id={id}
              name="email"
              type="email"
              autoComplete="email"
              defaultValue="jess@alphaplumbing.ca"
            />
          )}
        </Field>
        <Field
          label="Choose a password"
          labelAside={
            <span className="text-faint text-[13px] leading-4 font-semibold">
              12 characters or more
            </span>
          }
        >
          {(id) => (
            <PasswordInput id={id} name="password" autoComplete="new-password" minLength={12} />
          )}
        </Field>
        <Button type="submit" full className="h-12" working={working && "Joining"}>
          Accept and join
        </Button>
        <div className="flex items-center justify-between gap-4 rounded-[16px] bg-[#f7f9fb] px-4 py-3">
          <div className="min-w-0">
            <p className="text-body text-ink font-medium">Team member</p>
            <p className="text-meta text-faint">Approves changes, never budgets or billing</p>
          </div>
          <Chip tone="brand">Your role</Chip>
        </div>
      </AuthCard>
    </AuthShell>
  );
}
