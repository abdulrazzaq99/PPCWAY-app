"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Chip, PwCard } from "@/components/pw/shell";
import { cn } from "@/lib/cn";

/*
  The campaign list, from the handoff: a filter, a search box and one row per
  campaign with what it spent and what it brought. Every figure is read from the
  merchant's own Google Ads account.

  The handoff's row also carries a fifteen-day sparkline and a Learning chip.
  Both wait on the local mirror: Google gives us the window's totals in one read,
  and a line per campaign per day would be another read for every row.
*/
type Row = {
  campaign_id: string;
  name: string;
  status: string;
  leads: number;
  cost: number;
  cost_per_lead: number;
  budget: number;
};

type Summary = {
  read: boolean;
  trouble?: string;
  reconnect?: boolean;
  /** Connected, but they have not said which of their accounts to read. */
  choose?: boolean;
  currency?: string;
  days?: number;
  campaigns?: Row[];
};

const FILTERS = ["All", "Active", "Paused"] as const;

export function CampaignList({ initial }: { initial: Summary }) {
  const [summary, setSummary] = useState(initial);
  const [days, setDays] = useState(initial.days ?? 30);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("All");
  const [find, setFind] = useState("");
  const [asks, setAsks] = useState(0);

  useEffect(() => {
    if (asks === 0) return;
    let stop = false;
    fetch(`/api/ads/summary?days=${days}`, { cache: "no-store" })
      .then((r) => r.json() as Promise<Summary>)
      .then((said) => !stop && setSummary(said))
      .catch(() => undefined);
    return () => {
      stop = true;
    };
  }, [asks, days]);

  const rows = (summary.campaigns ?? []).filter((row) => {
    const active = row.status === "ENABLED";
    if (filter === "Active" && !active) return false;
    if (filter === "Paused" && active) return false;
    return row.name.toLowerCase().includes(find.trim().toLowerCase());
  });
  const currency = summary.currency ?? "";

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="border-pw-border bg-pw-card flex rounded-[10px] border p-[3px]">
          {FILTERS.map((name) => (
            <button
              key={name}
              type="button"
              onClick={() => setFilter(name)}
              className={cn(
                "rounded-[8px] px-3 py-[6px] text-[14px] font-semibold",
                filter === name ? "bg-pw-blue text-white" : "text-pw-ink-600 hover:bg-pw-muted",
              )}
            >
              {name}
              {name === "All" && summary.campaigns ? ` ${summary.campaigns.length}` : ""}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <input
            value={find}
            onChange={(e) => setFind(e.target.value)}
            placeholder="Search campaigns"
            aria-label="Search campaigns"
            className="border-pw-border-input bg-pw-card h-[38px] w-[220px] rounded-[10px] border px-3 text-[14px]"
          />
          <div className="border-pw-border bg-pw-card flex rounded-[10px] border p-[3px]">
            {[7, 30, 90].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => {
                  setDays(n);
                  setAsks((a) => a + 1);
                }}
                className={cn(
                  "rounded-[8px] px-3 py-[6px] text-[14px] font-semibold",
                  days === n ? "bg-pw-blue text-white" : "text-pw-ink-600 hover:bg-pw-muted",
                )}
              >
                {n} days
              </button>
            ))}
          </div>
        </div>
      </div>

      <PwCard className="overflow-hidden">
        {rows.length === 0 ? (
          <div className="px-6 py-10 text-center">
            <p className="text-pw-ink-500 text-[15px]">
              {summary.read
                ? find || filter !== "All"
                  ? "No campaign matches that."
                  : "This account has no campaigns in this window."
                : (summary.trouble ?? "Connect your account to see your campaigns.")}
            </p>
            {summary.choose ? (
              <Link
                href="/welcome"
                className="bg-pw-blue hover:bg-pw-blue-hover mt-4 inline-block rounded-[10px] px-4 py-2 text-[14px] font-semibold text-white"
              >
                Choose your account
              </Link>
            ) : null}
          </div>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="border-pw-divider text-pw-ink-400 border-b text-[12px]">
                <th className="px-5 py-3 font-semibold sm:px-6">Campaign</th>
                <th className="px-3 py-3 text-right font-semibold">Budget a day</th>
                <th className="px-3 py-3 text-right font-semibold">Spend</th>
                <th className="px-3 py-3 text-right font-semibold">Leads</th>
                <th className="px-3 py-3 text-right font-semibold">Cost per lead</th>
                <th className="px-5 py-3 font-semibold sm:px-6">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.campaign_id}
                  className="border-pw-divider hover:bg-pw-row-hover border-b last:border-0"
                >
                  <td className="px-5 py-3 sm:px-6">
                    <Link
                      href={`/campaigns/${row.campaign_id}`}
                      className="text-[15px] font-semibold hover:underline"
                    >
                      {row.name}
                    </Link>
                  </td>
                  <td className="pw-num px-3 py-3 text-right text-[15px]">
                    {row.budget ? money(row.budget, currency) : "—"}
                  </td>
                  <td className="pw-num px-3 py-3 text-right text-[15px]">
                    {money(row.cost, currency)}
                  </td>
                  <td className="pw-num px-3 py-3 text-right text-[15px]">
                    {Math.round(row.leads)}
                  </td>
                  <td className="pw-num px-3 py-3 text-right text-[15px]">
                    {row.cost_per_lead ? money(row.cost_per_lead, currency) : "—"}
                  </td>
                  <td className="px-5 py-3 sm:px-6">
                    <Chip tone={row.status === "ENABLED" ? "good" : "neutral"}>
                      {row.status === "ENABLED" ? "Active" : "Paused"}
                    </Chip>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </PwCard>

      <p className="text-pw-ink-400 text-[13px] leading-[20px]">
        Pausing, resuming and budget changes are not switched on yet. When they are, each one
        becomes a change you approve, with the before and after shown and thirty days to undo it.
      </p>
    </>
  );
}

export function money(amount: number, currency = ""): string {
  const sign = !currency || currency === "CAD" || currency === "USD" ? "$" : "";
  return `${sign}${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
