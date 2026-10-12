"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { AuthCard, AuthShell } from "@/components/auth/auth-shell";
import { Button, LinkButton, TextLink } from "@/components/ui/button";

/*
  Confirming an address from the link in an email. It happens on arrival: making
  somebody press a button to finish something they already chose by clicking the
  link is a step for nobody's benefit.
*/
function Verifying() {
  const token = useSearchParams().get("token") ?? "";
  // A link with no token is wrong before anything is asked, so it is decided
  // at render rather than by setting state inside an effect.
  const [state, setState] = useState<"working" | "done" | "failed">(token ? "working" : "failed");
  const [trouble, setTrouble] = useState(
    token
      ? ""
      : "That link is missing its token, which usually means an email client cut it short.",
  );
  const [again, setAgain] = useState("");

  useEffect(() => {
    if (!token) return;
    let stop = false;
    fetch("/api/auth/verify", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ token }),
    })
      .then(async (res) => {
        if (stop) return;
        if (res.ok) {
          setState("done");
          return;
        }
        const said = (await res.json().catch(() => ({}))) as { error?: string };
        setState("failed");
        setTrouble(said.error ?? "That link has been used already, or has expired.");
      })
      .catch(() => {
        if (!stop) {
          setState("failed");
          setTrouble("We could not reach the service.");
        }
      });
    return () => {
      stop = true;
    };
  }, [token]);

  async function resend() {
    setAgain("sending");
    try {
      const res = await fetch("/api/auth/verify/resend", { method: "POST" });
      setAgain(res.ok ? "sent" : "failed");
    } catch {
      setAgain("failed");
    }
  }

  return (
    <AuthShell
      headline="Confirming your email."
      body="This proves the address is yours, so we can send you the audit, the weekly summary and anything urgent about your account."
      footnote="You only have to do this once."
      below={
        <>
          Something wrong? <TextLink href="/help">Ask us</TextLink>
        </>
      }
    >
      {state === "working" ? (
        <AuthCard title="One moment">
          <p className="text-muted text-[15px] leading-[23px]">Checking your link…</p>
        </AuthCard>
      ) : state === "done" ? (
        <AuthCard title="That is confirmed">
          <p className="text-muted text-[15px] leading-[23px]">
            Your address is confirmed and your account is ready.
          </p>
          <LinkButton href="/home" full>
            Go to your dashboard
          </LinkButton>
        </AuthCard>
      ) : (
        <AuthCard title="That link did not work">
          <p className="text-muted text-[15px] leading-[23px]">{trouble}</p>
          {again === "sent" ? (
            <p className="text-[15px] leading-[23px] font-semibold">
              A new one is on its way. It works for two days.
            </p>
          ) : (
            <Button type="button" onClick={resend} full working={again === "sending" && "Sending"}>
              Send me another
            </Button>
          )}
          {again === "failed" ? (
            <p className="text-muted text-[14px] leading-[21px]">
              We could not send another. Sign in first, then try from your dashboard.
            </p>
          ) : null}
          <LinkButton href="/login" variant="secondary" full>
            Sign in
          </LinkButton>
        </AuthCard>
      )}
    </AuthShell>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense>
      <Verifying />
    </Suspense>
  );
}
