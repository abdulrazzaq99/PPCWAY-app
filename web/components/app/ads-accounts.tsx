"use client";

import { ArrowClockwise, CheckCircle, WarningCircle } from "@phosphor-icons/react/dist/ssr";
import { useEffect, useState } from "react";
import { Card } from "@/components/audit/shell";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

/*
  Which Google Ads account to read. Google is asked what this permission reaches,
  and each one is shown as it is: the ones we can read are choosable, and the ones
  we cannot say why in their own line rather than appearing as a blank row.
*/
type Account = {
  customer_id: string;
  name: string;
  is_manager: boolean;
  currency: string;
  time_zone: string;
  readable: boolean;
  trouble: string;
};

function pretty(id: string): string {
  return id.length === 10 ? `${id.slice(0, 3)}-${id.slice(3, 6)}-${id.slice(6)}` : id;
}

export function AdsAccounts({
  chosen,
  onChosen,
}: {
  chosen: string;
  onChosen: (customerId: string, name: string) => void;
}) {
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [trouble, setTrouble] = useState("");
  const [saving, setSaving] = useState("");
  // Bumped by the button; asking Google again is the effect's whole job.
  const [asks, setAsks] = useState(0);

  useEffect(() => {
    let stop = false;
    fetch("/api/ads/accounts", { cache: "no-store" })
      .then(async (res) => {
        const said = (await res.json()) as { accounts?: Account[]; error?: string };
        if (stop) return;
        setAccounts(res.ok ? (said.accounts ?? []) : []);
        if (!res.ok) setTrouble(said.error ?? "Google would not answer.");
      })
      .catch(() => {
        if (stop) return;
        setAccounts([]);
        setTrouble("We could not reach the service.");
      });
    return () => {
      stop = true;
    };
  }, [asks]);

  function lookAgain() {
    setTrouble("");
    setAccounts(null);
    setAsks((n) => n + 1);
  }

  async function choose(account: Account) {
    setSaving(account.customer_id);
    try {
      const res = await fetch("/api/ads/choose", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ customer_id: account.customer_id }),
      });
      if (res.ok) {
        onChosen(account.customer_id, account.name);
      } else {
        const said = (await res.json().catch(() => ({}))) as { error?: string };
        setTrouble(said.error ?? "We could not save that choice.");
      }
    } catch {
      setTrouble("We could not reach the service.");
    } finally {
      setSaving("");
    }
  }

  return (
    <Card className="mt-6 overflow-hidden">
      <div className="border-line-soft flex flex-wrap items-center justify-between gap-3 border-b px-5 py-5 sm:px-7">
        <div>
          <h2 className="text-[20px] leading-[26px] font-semibold">Your Google Ads accounts</h2>
          <p className="text-muted mt-1 text-[15px] leading-[22px]">
            Pick the one your ads run in. We read it; we change nothing.
          </p>
        </div>
        <Button type="button" variant="secondary" size="sm" onClick={lookAgain}>
          <ArrowClockwise aria-hidden size={15} weight="bold" />
          Look again
        </Button>
      </div>

      {trouble ? (
        <p className="text-red border-line-soft border-b px-5 py-4 text-[15px] leading-[21px] sm:px-7">
          {trouble}
        </p>
      ) : null}

      {accounts === null ? (
        <p className="text-muted px-5 py-6 text-[15px] sm:px-7">Asking Google…</p>
      ) : accounts.length === 0 ? (
        <p className="text-muted px-5 py-6 text-[15px] leading-[22px] sm:px-7">
          Google says this permission reaches no accounts. If your ads live under a different Google
          login, connect again and choose that one.
        </p>
      ) : (
        <ul className="divide-line-soft divide-y">
          {accounts.map((account) => {
            const picked = chosen === account.customer_id;
            return (
              <li
                key={account.customer_id}
                className={cn(
                  "flex flex-wrap items-center justify-between gap-4 px-5 py-4 sm:px-7",
                  picked && "bg-brand-tint",
                )}
              >
                <div className="min-w-0">
                  <p className="flex items-center gap-2 text-[16px] leading-[21px] font-semibold">
                    {account.name || "Unnamed account"}
                    {picked ? (
                      <CheckCircle aria-hidden size={16} weight="fill" className="text-brand" />
                    ) : null}
                  </p>
                  <p className="text-faint mt-1 text-[13px] leading-[18px]">
                    {pretty(account.customer_id)}
                    {account.currency ? ` · ${account.currency}` : ""}
                    {account.is_manager ? " · manager account" : ""}
                  </p>
                  {account.trouble ? (
                    <p className="text-amber-dark mt-2 flex items-start gap-2 text-[13px] leading-[19px]">
                      <WarningCircle
                        aria-hidden
                        size={15}
                        weight="fill"
                        className="mt-[2px] shrink-0"
                      />
                      {account.trouble}
                    </p>
                  ) : null}
                </div>
                {account.readable && !account.is_manager ? (
                  <Button
                    type="button"
                    size="sm"
                    variant={picked ? "secondary" : "primary"}
                    onClick={() => void choose(account)}
                    working={saving === account.customer_id && "Saving"}
                  >
                    {picked ? "Chosen" : "Read this one"}
                  </Button>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
