"use client";

import { useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { AuthCard, AuthShell } from "@/components/auth/auth-shell";
import { GoogleButton } from "@/components/auth/google-button";
import { Button, TextLink } from "@/components/ui/button";
import { Field, Input, PasswordInput } from "@/components/ui/field";

/*
  Two frames share this route.
  Plain: "Welcome back". With ?reason=signed-out: "You were signed out for safety",
  shown after a password change ended every other session.
*/
export default function LoginPage() {
  const params = useSearchParams();
  const signedOut = params.get("reason") === "signed-out";
  const [working, setWorking] = useState(false);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
  }

  const shell = signedOut
    ? {
        headline: "You were signed out for safety.",
        body: "Your password was changed on another device at 4:02 pm, so every other session ended. Sign in again and you will land back on Approvals, where you were.",
        footnote: (
          <>
            Not you who changed it?{" "}
            <TextLink href="/forgot-password" size={14} className="text-white hover:text-white">
              Reset your password straight away.
            </TextLink>
          </>
        ),
        below: (
          <>
            Didn&rsquo;t change your password?{" "}
            <TextLink href="/forgot-password">Secure my account</TextLink>
          </>
        ),
        title: "Sign in again",
        cta: "Sign in and carry on",
      }
    : {
        headline: "Google Ads that look after themselves.",
        body: "We write the campaign, watch it every day, and explain every change in plain words. You approve anything that matters.",
        footnote: "Free for 14 days. No card needed to look around.",
        below: (
          <>
            New to PPCWay? <TextLink href="/signup">Create an account</TextLink>
          </>
        ),
        title: "Welcome back",
        cta: "Sign in",
      };

  return (
    <AuthShell
      headline={shell.headline}
      body={shell.body}
      footnote={shell.footnote}
      below={shell.below}
    >
      <AuthCard title={shell.title} onSubmit={submit} intro={null}>
        <GoogleButton />
        <p className="text-faint text-[13px] leading-4 font-medium">or use your email</p>
        <Field label="Email">
          {(id) => (
            <Input
              id={id}
              name="email"
              type="email"
              autoComplete="email"
              placeholder="you@yourbusiness.ca"
              defaultValue="dana@alphaplumbing.ca"
            />
          )}
        </Field>
        <Field
          label="Password"
          labelAside={
            <TextLink href="/forgot-password" size={13}>
              Forgot it?
            </TextLink>
          }
        >
          {(id) => (
            <PasswordInput
              id={id}
              name="password"
              autoComplete="current-password"
              defaultValue="correct horse"
            />
          )}
        </Field>
        <Button type="submit" full className="h-12" working={working && "Signing in"}>
          {shell.cta}
        </Button>
      </AuthCard>
    </AuthShell>
  );
}
