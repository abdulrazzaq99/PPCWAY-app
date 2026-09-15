"use client";

import { useState, type FormEvent } from "react";
import { AuthCard, AuthShell } from "@/components/auth/auth-shell";
import { GoogleButton } from "@/components/auth/google-button";
import { Button, TextLink } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, Input, PasswordInput } from "@/components/ui/field";

export default function SignupPage() {
  const [agreed, setAgreed] = useState(true);
  const [working, setWorking] = useState(false);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!agreed) return;
    setWorking(true);
  }

  return (
    <AuthShell
      headline="Your first campaign in about 15 minutes."
      body="Tell us about your business, connect Google Ads, and read the campaign we write before it goes anywhere. Nothing spends until you say yes."
      footnote="Free for 14 days. Cancel from Settings any time."
      below={
        <>
          Already have an account? <TextLink href="/login">Sign in</TextLink>
        </>
      }
    >
      <AuthCard title="Create your account" onSubmit={submit}>
        <GoogleButton label="Sign up with Google" />
        <p className="text-faint text-[13px] leading-4 font-medium">or use your email</p>
        <Field label="Work email">
          {(id) => (
            <Input
              id={id}
              name="email"
              type="email"
              autoComplete="email"
              placeholder="you@yourbusiness.ca"
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
        <Checkbox checked={agreed} onChange={setAgreed}>
          I agree to the Terms, and to PPCWay using my business details and my website&rsquo;s text
          to build and run my ads, as the Privacy Policy explains.
        </Checkbox>
        <Button type="submit" full className="h-12" working={working && "Creating your account"}>
          Create account
        </Button>
      </AuthCard>
    </AuthShell>
  );
}
