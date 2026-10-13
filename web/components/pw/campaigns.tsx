"use client";

import { useEffect, useState } from "react";
import { CampaignDetail, type Detail } from "@/components/pw/campaign-detail";
import { Chip, Pill, PillGroup, PwCard } from "@/components/pw/shell";
import { cn } from "@/lib/cn";

/*
  Campaigns, laid out as the handoff draws them: the filter pills, a table with
  a leads trend per row, and the chosen campaign opening underneath rather than
  on a page of its own. Picking a row and reading its keywords is one movement,
  and the list stays in sight.

  Every figure is read from the merchant's own Google Ads account.
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
  choose?: boolean;
  currency?: string;
  days?: number;
  campaigns?: Row[];
};

const FILTERS = ["All", "Active", "Paused"] as const;

export function money(amount: number, currency = ""): string {
  const sign = !currency || currency === "CAD" || currency === "USD" ? "$" : "";
  return `${sign}${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function CampaignList({ initial, days: initialDays }: { initial: Summary; days: number }) {
  const [summary, setSummary] = useState(initial);
  const [days, setDays] = useState(initialDays);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("All");
  const [find, setFind] = useState("");
  const [chosen, setChosen] = useState<string>("");
  const [detail, setDetail] = useState<Detail | null>(null);
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

  useEffect(() => {
    if (!chosen) return;
    let stop = false;
    fetch(`/api/ads/campaigns/${chosen}?days=${days}`, { cache: "no-store" })
      .then((r) => r.json() as Promise<Detail>)
      .then((said) => {
        if (!stop) setDetail(said);
      })
      .catch(() => undefined);
    return () => {
      stop = true;
    };
  }, [chosen, days]);

  const rows = (summary.campaigns ?? []).filter((row) => {
    const active = row.status === "ENABLED";
    if (filter === "Active" && !active) return false;
    if (filter === "Paused" && active) return false;
    return row.name.toLowerCase().includes(find.trim().toLowerCase());
  });
  const currency = summary.currency ?? "";
  const most = Math.max(1, ...rows.map((r) => r.cost));

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <PillGroup>
          {FILTERS.map((name) => (
            <Pill key={name} active={filter === name} onClick={() => setFilter(name)}>
              {name}
              {name === "All" && summary.campaigns ? ` ${summary.campaigns.length}` : ""}
            </Pill>
          ))}
        </PillGroup>
        <div className="flex flex-wrap items-center gap-3">
          <PillGroup>
            {[7, 30, 90].map((n) => (
              <Pill
                key={n}
                active={days === n}
                onClick={() => {
                  setDays(n);
                  setAsks((a) => a + 1);
                }}
              >
                {n} days
              </Pill>
            ))}
          </PillGroup>
          <input
            value={find}
            onChange={(e) => setFind(e.target.value)}
            placeholder="Find a campaign"
            aria-label="Find a campaign"
            className="border-pw-border-input bg-pw-card h-[42px] w-[220px] rounded-full border px-4 text-[14px]"
          />
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
              <a
                href="/welcome"
                className="bg-pw-blue hover:bg-pw-blue-hover mt-4 inline-block rounded-[10px] px-4 py-2 text-[14px] font-semibold text-white"
              >
                Choose your account
              </a>
            ) : null}
          </div>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="border-pw-divider text-pw-ink-500 border-b text-[13px]">
                <th className="px-5 py-3 font-semibold sm:px-6">Campaign</th>
                <th className="px-3 py-3 font-semibold">Status</th>
                <th className="px-3 py-3 text-right font-semibold">Budget a day</th>
                <th className="px-3 py-3 text-right font-semibold">Spend</th>
                <th className="px-3 py-3 text-right font-semibold">Leads</th>
                <th className="px-3 py-3 text-right font-semibold">Cost per lead</th>
                <th className="px-5 py-3 font-semibold sm:px-6">Share of spend</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const here = chosen === row.campaign_id;
                return (
                  <tr
                    key={row.campaign_id}
                    onClick={() => setChosen(here ? "" : row.campaign_id)}
                    className={cn(
                      "border-pw-divider hover:bg-pw-row-hover cursor-pointer border-b last:border-0",
                      here && "bg-pw-blue-tint-2",
                    )}
                  >
                    <td
                      className={cn(
                        "max-w-[260px] truncate py-3 pl-5 text-[15px] font-semibold sm:pl-6",
                        here && "border-pw-blue border-l-[3px] pl-[17px] sm:pl-[21px]",
                      )}
                    >
                      {row.name}
                    </td>
                    <td className="px-3 py-3">
                      <Chip tone={row.status === "ENABLED" ? "good" : "neutral"}>
                        {row.status === "ENABLED" ? "Active" : "Paused"}
                      </Chip>
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
                      {/* A day-by-day trend needs the local mirror; until then
                          this shows where the money actually went. */}
                      <span
                        aria-label={`${Math.round((row.cost / most) * 100)}% of the largest spend`}
                        className="bg-pw-track block h-[8px] w-[120px] overflow-hidden rounded-full"
                      >
                        <span
                          className="bg-pw-blue block h-full rounded-full"
                          style={{ width: `${Math.max(3, (row.cost / most) * 100)}%` }}
                        />
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </PwCard>

      {chosen ? (
        // The answer arrives or it does not; either way the row stays chosen.
        detail && detail.campaign_id === chosen ? (
          <CampaignDetail detail={detail} onClose={() => setChosen("")} />
        ) : (
          <PwCard className="p-6">
            <p className="text-pw-ink-500 text-[15px]">Reading that campaign…</p>
          </PwCard>
        )
      ) : null}

      <p className="text-pw-ink-400 text-[13px] leading-[20px]">
        Pausing, resuming and budget changes are not switched on yet. When they are, each one
        becomes a change you approve, with the before and after shown and thirty days to undo it.
      </p>
    </>
  );
}
