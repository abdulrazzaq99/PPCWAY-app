"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Chip, PwCard } from "@/components/pw/shell";

/*
  Which of their Google Ads accounts we read. Google is asked what the
  permission reaches, and each account is shown as it is: the ones we can read
  are choosable, and the ones we cannot say why in their own line rather than
  appearing as a blank row.
*/
type Account = {
  customer_id: string;
  name: string;
  is_manager: boolean;
  currency: string;
  readable: boolean;
  trouble: string;
};

function pretty(id: string): string {
  return id.length === 10 ? `${id.slice(0, 3)}-${id.slice(3, 6)}-${id.slice(6)}` : id;
}

export function AccountPicker({ chosen = "" }: { chosen?: string }) {
  const router = useRouter();
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [trouble, setTrouble] = useState("");
  const [saving, setSaving] = useState("");
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
        if (!stop) {
          setAccounts([]);
          setTrouble("We could not reach the service.");
        }
      });
    return () => {
      stop = true;
    };
  }, [asks]);

  async function choose(account: Account) {
    setSaving(account.customer_id);
    try {
      const res = await fetch("/api/ads/choose", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ customer_id: account.customer_id }),
      });
      if (res.ok) {
        router.push("/home");
        router.refresh();
        return;
      }
      const said = (await res.json().catch(() => ({}))) as { error?: string };
      setTrouble(said.error ?? "We could not save that choice.");
    } catch {
      setTrouble("We could not reach the service.");
    } finally {
      setSaving("");
    }
  }

  return (
    <PwCard className="overflow-hidden">
      <div className="border-pw-divider flex flex-wrap items-center justify-between gap-3 border-b px-5 py-5 sm:px-6">
        <div>
          <h2 className="text-[17px] leading-[22px] font-semibold">Your Google Ads accounts</h2>
          <p className="text-pw-ink-500 mt-1 text-[14px]">
            Pick the one your ads run in. We read it; we change nothing.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setTrouble("");
            setAccounts(null);
            setAsks((n) => n + 1);
          }}
          className="border-pw-border-strong hover:bg-pw-muted rounded-[10px] border px-3 py-[6px] text-[14px] font-semibold"
        >
          Look again
        </button>
      </div>

      {trouble ? (
        <p className="text-pw-bad border-pw-divider border-b px-5 py-4 text-[14px] sm:px-6">
          {trouble}
        </p>
      ) : null}

      {accounts === null ? (
        <p className="text-pw-ink-500 px-5 py-6 text-[15px] sm:px-6">Asking Google…</p>
      ) : accounts.length === 0 ? (
        <p className="text-pw-ink-500 px-5 py-6 text-[15px] leading-[23px] sm:px-6">
          Google says this permission reaches no accounts. If your ads live under a different Google
          login, connect again and choose that one.
        </p>
      ) : (
        <ul className="divide-pw-divider divide-y">
          {accounts.map((account) => {
            const picked = chosen === account.customer_id;
            return (
              <li
                key={account.customer_id}
                className="flex flex-wrap items-center justify-between gap-4 px-5 py-4 sm:px-6"
              >
                <div className="min-w-0">
                  <p className="flex flex-wrap items-center gap-2 text-[16px] font-semibold">
                    {account.name || "Unnamed account"}
                    {picked ? <Chip tone="info">Chosen</Chip> : null}
                  </p>
                  <p className="text-pw-ink-400 mt-1 text-[13px]">
                    {pretty(account.customer_id)}
                    {account.currency ? ` · ${account.currency}` : ""}
                    {account.is_manager ? " · manager account" : ""}
                  </p>
                  {account.trouble ? (
                    <p className="text-pw-warn-ink mt-2 text-[13px] leading-[19px]">
                      {account.trouble}
                    </p>
                  ) : null}
                </div>
                {account.readable && !account.is_manager ? (
                  <button
                    type="button"
                    onClick={() => void choose(account)}
                    disabled={saving === account.customer_id}
                    className="bg-pw-blue hover:bg-pw-blue-hover rounded-[10px] px-4 py-2 text-[14px] font-semibold text-white disabled:opacity-70"
                  >
                    {saving === account.customer_id
                      ? "Saving…"
                      : picked
                        ? "Chosen"
                        : "Read this one"}
                  </button>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </PwCard>
  );
}
