"use client";

import { ArrowRight, LockSimple } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AuditPage, Card } from "@/components/audit/shell";
import { Button, LinkButton } from "@/components/ui/button";

/*
  What a signed-in person sees. Three things, in the order they matter: what their
  last audit found, what connecting Google Ads would add to it, and the audits
  they have run.

  Nothing invented. The dashboard drawn in Figma shows a month of calls and spend
  from an account nobody has connected yet; it stays reachable at ?view= for
  showing the design, and is never what somebody is shown about themselves.
*/
type Person = { email: string; name: string };
type Run = { id: string; site: string; status: string };
type AdsStatus = { connected: boolean; customer_id?: string; customer_name?: string };

const LOCKED = [
  "Wasted spend on search terms",
  "Quality Score by keyword",
  "Budget lost to impression share",
  "Ad disapprovals and policy issues",
];

export function SignedInHome({ person }: { person: Person }) {
  const [runs, setRuns] = useState<Run[] | null>(null);
  const [ads, setAds] = useState<AdsStatus | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [trouble, setTrouble] = useState("");

  useEffect(() => {
    let stop = false;
    Promise.all([
      fetch("/api/audit/mine", { cache: "no-store" })
        .then((r) => (r.ok ? (r.json() as Promise<Run[]>) : []))
        .catch(() => []),
      fetch("/api/ads/status", { cache: "no-store" })
        .then((r) => (r.ok ? (r.json() as Promise<AdsStatus>) : { connected: false }))
        .catch(() => ({ connected: false })),
    ]).then(([mine, status]) => {
      if (stop) return;
      setRuns(mine);
      setAds(status);
    });
    return () => {
      stop = true;
    };
  }, []);

  async function connect() {
    setConnecting(true);
    setTrouble("");
    try {
      const res = await fetch("/api/ads/connect", { method: "POST" });
      const said = (await res.json().catch(() => ({}))) as { url?: string; error?: string };
      if (res.ok && said.url) {
        window.location.href = said.url;
        return;
      }
      setTrouble(said.error ?? "Connecting Google Ads is not available right now.");
    } catch {
      setTrouble("We could not reach the service. Try again in a minute.");
    } finally {
      setConnecting(false);
    }
  }

  const latest = runs?.find((r) => r.status === "done") ?? runs?.[0];
  const first = person.name.split(" ")[0] || person.email;

  return (
    <AuditPage wide>
      <h1 className="text-[32px] leading-[40px] font-semibold sm:text-[42px] sm:leading-[50px]">
        {first}, here is where you are.
      </h1>
      <p className="text-muted mt-4 max-w-[720px] text-[17px] leading-[27px]">
        {ads?.connected
          ? "Your Google Ads account is connected, so the next audit reads it too."
          : "Your free audit reads what Google shows the public. The four checks that cost you money are inside your own Google Ads account, and only you can open them."}
      </p>

      {!ads?.connected ? (
        <section className="bg-night mt-7 rounded-[26px] p-6 text-white sm:p-9">
          <div className="flex flex-col gap-7 lg:flex-row lg:items-center lg:justify-between">
            <div className="max-w-[620px]">
              <p className="text-brand-sky text-[13px] leading-4 font-semibold tracking-[0.08em] uppercase">
                The next step
              </p>
              <h2 className="display mt-2 text-[26px] leading-[32px] font-semibold sm:text-[32px] sm:leading-[38px]">
                Connect Google Ads to unlock the four checks that cost money.
              </h2>
              <ul className="mt-4 flex flex-col gap-2">
                {LOCKED.map((row) => (
                  <li key={row} className="text-night-faint flex items-center gap-3 text-[15px]">
                    <LockSimple aria-hidden size={15} weight="bold" className="shrink-0" />
                    {row}
                  </li>
                ))}
              </ul>
              <p className="text-night-faint mt-4 text-[14px] leading-[22px]">
                We read your account. We change nothing without your yes, and you can disconnect
                whenever you like.
              </p>
            </div>
            <div className="flex w-full flex-col gap-3 sm:w-auto lg:w-[260px]">
              <Button type="button" onClick={connect} full working={connecting && "Opening Google"}>
                Connect Google Ads
                <ArrowRight aria-hidden size={15} weight="bold" />
              </Button>
              {trouble ? (
                <p className="text-[13px] leading-[19px] text-white/80" role="alert">
                  {trouble}
                </p>
              ) : null}
            </div>
          </div>
        </section>
      ) : (
        <Card className="mt-7 flex flex-wrap items-center justify-between gap-4 p-5 sm:p-7">
          <div>
            <p className="text-[17px] leading-[22px] font-semibold">Google Ads connected</p>
            <p className="text-muted mt-1 text-[15px] leading-[21px]">
              {ads.customer_name || ads.customer_id
                ? `${ads.customer_name || "Account"} ${ads.customer_id}`
                : "Pick which account to read on your next audit."}
            </p>
          </div>
          <LinkButton href="/audit" size="sm">
            Run the audit again
            <ArrowRight aria-hidden size={15} weight="bold" />
          </LinkButton>
        </Card>
      )}

      <section className="mt-8">
        <h2 className="text-[22px] leading-[28px] font-semibold sm:text-[26px]">Your audit</h2>
        {runs === null ? (
          <p className="text-muted mt-3 text-[16px]">Looking…</p>
        ) : latest ? (
          <Card className="mt-4 flex flex-wrap items-center justify-between gap-4 p-5 sm:p-7">
            <div className="min-w-0">
              <p className="truncate text-[17px] leading-[22px] font-semibold">
                {latest.site.replace(/^https?:\/\//, "").replace(/\/$/, "")}
              </p>
              <p className="text-muted mt-1 text-[15px] leading-[21px]">
                {latest.status === "done"
                  ? "Your listing, your website and your competitors, as Google sees them."
                  : latest.status === "failed"
                    ? "That run did not finish."
                    : "Still running."}
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <LinkButton href={`/audit/${latest.id}`} size="sm">
                Open the report
              </LinkButton>
              {runs.length > 1 ? (
                <LinkButton href="/audit/mine" size="sm" variant="secondary">
                  All {runs.length}
                </LinkButton>
              ) : null}
            </div>
          </Card>
        ) : (
          <Card className="mt-4 p-5 sm:p-7">
            <p className="text-muted text-[16px] leading-[24px]">
              You have not run one yet. It takes about a minute and needs no account details.
            </p>
            <div className="mt-4">
              <LinkButton href="/audit">Run my free audit</LinkButton>
            </div>
          </Card>
        )}
      </section>

      <p className="text-faint mt-10 text-[14px] leading-[20px]">
        Looking for the dashboard drawn in Figma?{" "}
        <Link href="/overview?view=calls" className="text-brand font-semibold">
          It is here
        </Link>
        , with its sample numbers, until your own account fills it.
      </p>
    </AuditPage>
  );
}
