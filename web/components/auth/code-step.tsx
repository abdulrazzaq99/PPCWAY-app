"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { AuthCard } from "@/components/auth/auth-shell";
import { CodeField } from "@/components/auth/code-field";
import { Button } from "@/components/ui/button";

/*
  Signing in, or up, with six digits sent by email: the second half, after the
  address has been typed on the sign-in or sign-up card. The same card for both,
  because the backend treats them as one thing: an address it knows signs in to
  its account, and one it does not becomes a new account when the code comes back.
*/

/** What came of asking for a code. */
export type Asked =
  { ok: true; sent: boolean; waitSeconds: number; minutes: number } | { ok: false; error: string };

/** Ask for a code to be emailed to this address. */
export async function askForCode(email: string): Promise<Asked> {
  try {
    const res = await fetch("/api/auth/code", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email }),
    });
    const said = (await res.json().catch(() => ({}))) as {
      sent?: boolean;
      wait_seconds?: number;
      minutes?: number;
      error?: string;
    };
    if (!res.ok) return { ok: false, error: said.error ?? "We could not send a code just now." };
    return {
      ok: true,
      sent: Boolean(said.sent),
      waitSeconds: said.wait_seconds ?? 0,
      minutes: said.minutes ?? 10,
    };
  } catch {
    return { ok: false, error: "We could not reach the service. Try again in a minute." };
  }
}

/** A typed address worth sending to. The backend checks properly; this catches the empty box. */
export function looksLikeAnAddress(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

/** How long to wait before another code, when nothing else says. */
const COOLDOWN_SECONDS = 60;

export function CodeStep({
  email,
  name = "",
  next,
  first,
  cta,
  onBack,
}: {
  email: string;
  /** Only used when the address is new and this becomes a sign-up. */
  name?: string;
  /** Where to go afterwards; empty lets the server decide (staff land on the panel). */
  next: string;
  /** What asking for the code said, so the card can tell a new code from an earlier one. */
  first: Extract<Asked, { ok: true }>;
  cta: string;
  onBack: () => void;
}) {
  const router = useRouter();
  const [working, setWorking] = useState(false);
  const [trouble, setTrouble] = useState("");
  const [notice, setNotice] = useState(
    first.sent ? "" : "We sent a code a moment ago. Use that one, or wait for another.",
  );
  const [wait, setWait] = useState(first.sent ? COOLDOWN_SECONDS : first.waitSeconds);
  const [asking, setAsking] = useState(false);

  useEffect(() => {
    if (wait <= 0) return;
    const tick = window.setTimeout(() => setWait((left) => left - 1), 1000);
    return () => window.clearTimeout(tick);
  }, [wait]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const code = String(new FormData(event.currentTarget).get("code") ?? "").replace(/\D/g, "");
    if (code.length !== 6) {
      setTrouble("Type all six digits from the email.");
      return;
    }
    setWorking(true);
    setTrouble("");
    try {
      const res = await fetch("/api/auth/code/check", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, code, name }),
      });
      const said = (await res.json().catch(() => ({}))) as { error?: string; landing?: string };
      if (res.ok) {
        router.replace(next || said.landing || "/home");
        router.refresh();
        return;
      }
      setTrouble(said.error ?? "That code did not work. Ask for a new one.");
    } catch {
      setTrouble("We could not reach the service. Try again in a minute.");
    } finally {
      setWorking(false);
    }
  }

  async function another() {
    setAsking(true);
    setTrouble("");
    setNotice("");
    const said = await askForCode(email);
    setAsking(false);
    if (!said.ok) {
      setTrouble(said.error);
      return;
    }
    if (said.sent) {
      setNotice("A new code is on its way. The one before it no longer works.");
      setWait(COOLDOWN_SECONDS);
    } else {
      setWait(said.waitSeconds);
    }
  }

  return (
    <AuthCard
      title="Check your email"
      intro={
        <>
          We sent a six-digit code to <span className="text-pw-ink font-semibold">{email}</span>. It
          works once, for {first.minutes} minutes.
        </>
      }
      onSubmit={submit}
    >
      <CodeField label="Six-digit code" autoFocus />
      {notice ? (
        <p className="text-pw-ink-500 text-[14px] leading-[18px] font-medium" role="status">
          {notice}
        </p>
      ) : null}
      {trouble ? (
        <p className="text-red text-[14px] leading-[18px] font-medium" role="alert">
          {trouble}
        </p>
      ) : null}
      <Button type="submit" full className="h-12" working={working && "Checking"}>
        {cta}
      </Button>
      <div className="flex flex-wrap items-center justify-between gap-3 text-[13px] leading-4 font-semibold">
        <button
          type="button"
          onClick={onBack}
          className="text-brand hover:text-brand-dark tap focus-visible:ring-brand-bar rounded-sm focus-visible:ring-4 focus-visible:outline-none"
        >
          Use a different address
        </button>
        <button
          type="button"
          onClick={another}
          disabled={wait > 0 || asking}
          className="text-brand hover:text-brand-dark disabled:text-pw-ink-400 tap focus-visible:ring-brand-bar rounded-sm focus-visible:ring-4 focus-visible:outline-none disabled:cursor-default"
        >
          {asking ? "Sending" : wait > 0 ? `Send another in ${wait}s` : "Send another code"}
        </button>
      </div>
    </AuthCard>
  );
}
