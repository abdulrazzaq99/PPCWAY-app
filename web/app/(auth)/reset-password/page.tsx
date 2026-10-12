"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";
import { AuthCard, AuthShell } from "@/components/auth/auth-shell";
import { Button, LinkButton, TextLink } from "@/components/ui/button";
import { Field, PasswordInput } from "@/components/ui/field";

/*
  Setting a new password from the link in an email. Succeeding signs them in:
  somebody who can read that inbox owns the address, which is the same thing the
  confirmation link proves.
*/
function ResetForm() {
  const router = useRouter();
  const token = useSearchParams().get("token") ?? "";
  const [working, setWorking] = useState(false);
  const [trouble, setTrouble] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") ?? "");
    if (password !== String(form.get("again") ?? "")) {
      setTrouble("Those two do not match.");
      return;
    }
    setWorking(true);
    setTrouble("");
    try {
      const res = await fetch("/api/auth/reset", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ token, password }),
      });
      if (res.ok) {
        router.replace("/home");
        router.refresh();
        return;
      }
      const said = (await res.json().catch(() => ({}))) as { error?: string };
      setTrouble(said.error ?? "That link did not work.");
    } catch {
      setTrouble("We could not reach the service. Try again in a minute.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <AuthShell
      headline="Set a new password."
      body="Choose something you have not used elsewhere. Length does more for you than punctuation."
      footnote="Setting it signs you in on this device."
      below={
        <>
          Changed your mind? <TextLink href="/login">Sign in</TextLink>
        </>
      }
    >
      {!token ? (
        <AuthCard title="That link is incomplete">
          <p className="text-muted text-[15px] leading-[23px]">
            It is missing its token, which usually means the address was cut short by an email
            client. Ask for another link and open it from the message itself.
          </p>
          <LinkButton href="/forgot-password" full>
            Send me another
          </LinkButton>
        </AuthCard>
      ) : (
        <AuthCard title="Your new password" onSubmit={submit}>
          <Field label="New password" hint="At least 10 characters.">
            {(id) => (
              <PasswordInput
                id={id}
                name="password"
                autoComplete="new-password"
                required
                minLength={10}
              />
            )}
          </Field>
          <Field label="Again, to be sure">
            {(id) => (
              <PasswordInput
                id={id}
                name="again"
                autoComplete="new-password"
                required
                minLength={10}
              />
            )}
          </Field>
          {trouble ? (
            <p className="text-red text-[14px] leading-[18px] font-medium" role="alert">
              {trouble}
            </p>
          ) : null}
          <Button type="submit" full working={working && "Setting it"}>
            Set my password
          </Button>
        </AuthCard>
      )}
    </AuthShell>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetForm />
    </Suspense>
  );
}
