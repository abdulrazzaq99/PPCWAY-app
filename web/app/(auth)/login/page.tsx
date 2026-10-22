"use client";

import { Suspense, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthCard, AuthShell } from "@/components/auth/auth-shell";
import { GoogleButton } from "@/components/auth/google-button";
import { Button, TextLink } from "@/components/ui/button";
import { Field, Input, PasswordInput } from "@/components/ui/field";

/*
  Three frames share this route.
  Plain: "Welcome back". With ?reason=signed-out: "You were signed out for safety",
  shown after a password change ended every other session. With ?brand=brightpath:
  the white-label sign-in an agency's clients see at the agency's own address.
*/
function LoginPageInner() {
  const params = useSearchParams();
  const signedOut = params.get("reason") === "signed-out";
  const agency = params.get("brand") === "brightpath";
  const router = useRouter();
  const next = params.get("next") || "/home";
  const [working, setWorking] = useState(false);
  const [trouble, setTrouble] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setWorking(true);
    setTrouble("");
    try {
      const res = await fetch("/api/auth/password", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          email: String(form.get("email") ?? ""),
          password: String(form.get("password") ?? ""),
        }),
      });
      if (res.ok) {
        router.replace(next);
        router.refresh();
        return;
      }
      const said = (await res.json().catch(() => ({}))) as { error?: string };
      setTrouble(said.error ?? "That address and password do not match.");
    } catch {
      setTrouble("We could not reach the service. Try again in a minute.");
    } finally {
      setWorking(false);
    }
  }

  const shell = agency
    ? {
        headline: "Your ads, looked after by Brightpath.",
        body: "See your calls, what we changed and why, any time. Questions go straight to your account manager, Priya.",
        footnote: "app.brightpath.ca · Brightpath Media, Oakville",
        below: (
          <>
            No account yet? <TextLink href="#">Ask Priya for an invite</TextLink>
          </>
        ),
        title: "Sign in to see your ads",
        cta: "Sign in",
      }
    : signedOut
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
      brand={agency ? "brightpath" : "ppcway"}
    >
      <AuthCard title={shell.title} onSubmit={submit} intro={null}>
        <GoogleButton next={next} />
        <p className="text-faint text-[13px] leading-4 font-medium">or use your email</p>
        <Field label="Email">
          {(id) => (
            <Input
              id={id}
              name="email"
              type="email"
              autoComplete="email"
              placeholder="you@yourbusiness.ca"
              defaultValue={agency ? "owner@northgatehvac.ca" : "dana@alphaplumbing.ca"}
            />
          )}
        </Field>
        <Field
          label="Password"
          labelAside={
            <TextLink href="/forgot-password" size={13} className="tap">
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
        {trouble ? (
          <p className="text-red text-[14px] leading-[18px] font-medium" role="alert">
            {trouble}
          </p>
        ) : null}

        <Button type="submit" full className="h-12" working={working && "Signing in"}>
          {shell.cta}
        </Button>
      </AuthCard>
    </AuthShell>
  );
}

/* useSearchParams needs a Suspense boundary so the page can still be prerendered. */
export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginPageInner />
    </Suspense>
  );
}
