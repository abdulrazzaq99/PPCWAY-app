"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent, type MouseEvent } from "react";
import { AuthCard, AuthShell } from "@/components/auth/auth-shell";
import { CodeStep, askForCode, looksLikeAnAddress, type Asked } from "@/components/auth/code-step";
import { GoogleButton } from "@/components/auth/google-button";
import { Button, TextLink } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, Input, PasswordInput } from "@/components/ui/field";

/*
  Signing up with an address and a password, or a code by email instead of the
  password, beside Google's button. The account
  exists the moment this succeeds; the confirmation email is a second step and
  not a gate, because a business owner who cannot reach their inbox at that
  moment should still be able to look around.
*/
export function SignupForm() {
  const router = useRouter();
  const next = useSearchParams().get("next") || "/home";
  const [agreed, setAgreed] = useState(true);
  const [working, setWorking] = useState(false);
  const [trouble, setTrouble] = useState("");
  /* Set once a code has been asked for: the card becomes "Check your email". */
  const [codeFor, setCodeFor] = useState<{
    email: string;
    name: string;
    first: Extract<Asked, { ok: true }>;
  } | null>(null);
  const [asking, setAsking] = useState(false);
  /* Kept so "Use a different address" comes back with the form still filled. */
  const [typed, setTyped] = useState({ email: "", name: "" });

  /*
    No password: a code to the address, and the account is made when it comes
    back. Reads the name and address already typed in the same form.
  */
  async function emailCode(event: MouseEvent<HTMLButtonElement>) {
    if (!agreed) return;
    const form = event.currentTarget.form;
    const data = form ? new FormData(form) : null;
    const email = String(data?.get("email") ?? "").trim();
    const name = String(data?.get("name") ?? "").trim();
    setTyped({ email, name });
    if (!looksLikeAnAddress(email)) {
      setTrouble("Type your work email first, and we will send a code to it.");
      return;
    }
    setAsking(true);
    setTrouble("");
    const said = await askForCode(email);
    setAsking(false);
    if (said.ok) setCodeFor({ email, name, first: said });
    else setTrouble(said.error);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!agreed) return;
    const form = new FormData(event.currentTarget);
    setWorking(true);
    setTrouble("");
    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          email: String(form.get("email") ?? ""),
          password: String(form.get("password") ?? ""),
          name: String(form.get("name") ?? ""),
        }),
      });
      if (res.ok) {
        router.replace(next);
        router.refresh();
        return;
      }
      const said = (await res.json().catch(() => ({}))) as { error?: string };
      setTrouble(said.error ?? "We could not make that account.");
    } catch {
      setTrouble("We could not reach the service. Try again in a minute.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <AuthShell
      headline="Your first campaign in about 15 minutes."
      body="Tell us about your business, connect Google Ads, and read the campaign we write before it goes anywhere. Nothing spends until you say yes."
      footnote="Free for 14 days. Cancel from Settings any time."
      below={
        <>
          Already have an account?{" "}
          <TextLink href={next === "/home" ? "/login" : `/login?next=${encodeURIComponent(next)}`}>
            Sign in
          </TextLink>
        </>
      }
    >
      {codeFor ? (
        <CodeStep
          email={codeFor.email}
          name={codeFor.name}
          next={next}
          first={codeFor.first}
          cta="Continue"
          onBack={() => setCodeFor(null)}
        />
      ) : (
        <AuthCard title="Create your account" onSubmit={submit}>
          <GoogleButton label="Sign up with Google" next={next} />
          <p className="text-faint text-[13px] leading-4 font-medium">or use your email</p>

          <Field label="Your name">
            {(id) => (
              <Input
                id={id}
                name="name"
                autoComplete="name"
                placeholder="Dana Reid"
                defaultValue={typed.name}
              />
            )}
          </Field>

          <Field label="Work email">
            {(id) => (
              <Input
                id={id}
                name="email"
                type="email"
                autoComplete="email"
                required
                placeholder="dana@alphaplumbing.ca"
                defaultValue={typed.email}
              />
            )}
          </Field>

          <Field label="Password" hint="At least 10 characters. Length matters more than symbols.">
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

          <Checkbox checked={agreed} onChange={setAgreed}>
            I agree to the <TextLink href="/terms">terms</TextLink> and the{" "}
            <TextLink href="/privacy">privacy policy</TextLink>.
          </Checkbox>

          {trouble ? (
            <p className="text-red text-[14px] leading-[18px] font-medium" role="alert">
              {trouble}
            </p>
          ) : null}

          <Button type="submit" full working={working && "Making your account"} disabled={!agreed}>
            Create account
          </Button>
          <Button
            variant="secondary"
            full
            onClick={emailCode}
            working={asking && "Sending a code"}
            disabled={!agreed}
          >
            Email me a code instead
          </Button>
        </AuthCard>
      )}
    </AuthShell>
  );
}
