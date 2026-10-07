"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AuditPage, Card } from "@/components/audit/shell";
import { LinkButton } from "@/components/ui/button";

/*
  The landing after Google. The code is exchanged once, by the backend; this page
  says what happened in plain words and goes nowhere on its own.
*/
export function AdsCallback({
  code,
  state,
  refused,
}: {
  code: string;
  state: string;
  refused: string;
}) {
  // What Google sent back is known at render: only the exchange needs an effect.
  const missing = refused
    ? refused === "access_denied"
      ? "You said no to Google, so nothing was connected. Nothing changed either."
      : `Google stopped the connection: ${refused}`
    : !code || !state
      ? "That link is missing what Google sends back. Start the connection again."
      : "";

  const [said, setSaid] = useState<"working" | "done" | "failed">("working");
  const [why, setWhy] = useState("");

  useEffect(() => {
    if (missing) return;
    let stop = false;
    fetch("/api/ads/finish", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ code, state }),
    })
      .then(async (res) => {
        if (stop) return;
        if (res.ok) {
          setSaid("done");
          return;
        }
        const problem = (await res.json().catch(() => ({}))) as { error?: string };
        setSaid("failed");
        setWhy(problem.error ?? "We could not finish the connection.");
      })
      .catch(() => {
        if (!stop) {
          setSaid("failed");
          setWhy("We could not reach the service to finish the connection.");
        }
      });
    return () => {
      stop = true;
    };
  }, [code, state, missing]);

  const state_ = missing ? "failed" : said;
  const reason = missing || why;

  return (
    <AuditPage>
      <h1 className="text-[32px] leading-[38px] font-semibold sm:text-[40px] sm:leading-[48px]">
        {state_ === "working"
          ? "Connecting your Google Ads…"
          : state_ === "done"
            ? "Your Google Ads account is connected."
            : "That connection did not finish."}
      </h1>
      <Card className="mt-6 p-5 sm:p-7">
        {state_ === "working" ? (
          <p className="text-muted text-[16px] leading-[24px]">
            Exchanging what Google gave us for a permission we can keep. A moment.
          </p>
        ) : state_ === "done" ? (
          <>
            <p className="text-muted text-[16px] leading-[24px]">
              We can now read your account: what your ads spent, which searches they showed for, and
              what Google thinks of your keywords. We change nothing without your yes, and you can
              disconnect whenever you like.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <LinkButton href="/overview">See what it unlocked</LinkButton>
              <LinkButton href="/audit" variant="secondary">
                Run the audit again
              </LinkButton>
            </div>
          </>
        ) : (
          <>
            <p className="text-muted text-[16px] leading-[24px]">{reason}</p>
            <div className="mt-5">
              <LinkButton href="/overview">Back to your account</LinkButton>
            </div>
          </>
        )}
      </Card>
      <p className="text-faint mt-5 text-[14px] leading-[20px]">
        Trouble?{" "}
        <Link href="/help" className="text-brand font-semibold">
          How connecting works
        </Link>
      </p>
    </AuditPage>
  );
}
