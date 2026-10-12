"use client";

import Link from "next/link";
import { useState } from "react";
import { money } from "@/components/pw/campaigns";
import { Chip, Kpi, PwCard } from "@/components/pw/shell";
import { cn } from "@/lib/cn";

/*
  One campaign. The handoff gives it five tabs; four of them are read from the
  account today. Change history waits on the change log, which is the first
  thing built when PPCway starts writing — and until it does, an empty history
  is the truthful answer: we have changed nothing.
*/
type Keyword = {
  keyword: string;
  match: string;
  quality_score: number;
  clicks: number;
  leads: number;
  cost: number;
  cost_per_lead: number;
};
type Term = { term: string; clicks: number; leads: number; cost: number; waste: boolean };
type Ad = {
  ad_group: string;
  headlines: string[];
  approval: string;
  status: string;
  impressions: number;
  clicks: number;
  click_rate: number;
};

export type Detail = {
  read: boolean;
  trouble?: string;
  campaign_id: string;
  name: string;
  status: string;
  currency: string;
  days: number;
  leads: number;
  cost: number;
  clicks: number;
  impressions: number;
  budget: number;
  cost_per_lead: number;
  lead_rate: number;
  lost_to_budget: number;
  lost_to_rank: number;
  impression_share: number;
  keywords: Keyword[];
  terms: Term[];
  ads: Ad[];
};

const TABS = ["Overview", "Keywords", "Search terms", "Ads", "Change history"] as const;

export function CampaignDetail({ detail }: { detail: Detail }) {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Overview");
  const c = detail.currency;

  if (!detail.read) {
    return (
      <PwCard className="p-6 sm:p-8">
        <p className="text-pw-ink-500 text-[16px]">
          {detail.trouble ?? "We could not read this campaign."}
        </p>
        <Link
          href="/campaigns"
          className="text-pw-blue mt-4 inline-block text-[15px] font-semibold"
        >
          ← All campaigns
        </Link>
      </PwCard>
    );
  }

  return (
    <>
      <PwCard className="flex flex-wrap items-center justify-between gap-4 p-5 sm:p-6">
        <div className="min-w-0">
          <Link href="/campaigns" className="text-pw-ink-500 text-[13px] font-semibold">
            ← All campaigns
          </Link>
          <h2 className="display mt-1 flex flex-wrap items-center gap-3 text-[22px] leading-[28px] font-semibold">
            {detail.name}
            <Chip tone={detail.status === "ENABLED" ? "good" : "neutral"}>
              {detail.status === "ENABLED" ? "Active" : "Paused"}
            </Chip>
          </h2>
          <p className="text-pw-ink-500 mt-1 text-[14px]">
            {detail.budget ? `${money(detail.budget, c)} a day` : "No daily budget set"} · last{" "}
            {detail.days} days
          </p>
        </div>
      </PwCard>

      <div className="border-pw-border bg-pw-card flex w-fit max-w-full overflow-x-auto rounded-[10px] border p-[3px]">
        {TABS.map((name) => (
          <button
            key={name}
            type="button"
            onClick={() => setTab(name)}
            className={cn(
              "rounded-[8px] px-3 py-[6px] text-[14px] font-semibold whitespace-nowrap",
              tab === name ? "bg-pw-blue text-white" : "text-pw-ink-600 hover:bg-pw-muted",
            )}
          >
            {name}
          </button>
        ))}
      </div>

      {tab === "Overview" ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <Kpi label="Leads" value={String(Math.round(detail.leads))} />
            <Kpi
              label="Cost per lead"
              value={detail.cost_per_lead ? money(detail.cost_per_lead, c) : "—"}
            />
            <Kpi label="Spend" value={money(detail.cost, c)} />
            <Kpi label="Clicks" value={detail.clicks.toLocaleString()} />
            <Kpi
              label="Lead rate"
              value={detail.clicks ? `${detail.lead_rate}%` : "—"}
              foot="Clicks that became an enquiry"
            />
            <Kpi
              label="Search share"
              value={detail.impression_share ? `${detail.impression_share}%` : "—"}
              chip={
                detail.lost_to_budget >= 5 ? (
                  <Chip tone="warn">Lost {detail.lost_to_budget}% to budget</Chip>
                ) : detail.lost_to_rank >= 20 ? (
                  <Chip tone="warn">Lost {detail.lost_to_rank}% to rank</Chip>
                ) : null
              }
              foot="How often your ad showed when it could have"
            />
          </div>
          {detail.lost_to_rank >= 20 ? (
            <PwCard className="p-5 sm:p-6">
              <p className="text-[15px] leading-[24px]">
                <strong className="font-semibold">
                  This campaign misses {detail.lost_to_rank}% of its searches because the ad ranks
                  too low, not because the budget runs out.
                </strong>{" "}
                More money would not fix that; better keywords, ads and landing pages would. The
                website audit checks the last of those.
              </p>
            </PwCard>
          ) : null}
        </>
      ) : null}

      {tab === "Keywords" ? (
        <Table
          empty="No keyword spent anything in this window."
          head={["Keyword", "Match", "Quality", "Clicks", "Leads", "Cost per lead"]}
          rows={detail.keywords.map((k) => [
            k.keyword,
            k.match,
            k.quality_score ? `${k.quality_score}/10` : "—",
            String(k.clicks),
            String(Math.round(k.leads)),
            k.cost_per_lead ? money(k.cost_per_lead, c) : "—",
          ])}
        />
      ) : null}

      {tab === "Search terms" ? (
        <Table
          empty="Nobody's search cost anything in this window."
          head={["What they typed", "Clicks", "Leads", "Cost", ""]}
          rows={detail.terms.map((t) => [
            t.term,
            String(t.clicks),
            String(Math.round(t.leads)),
            money(t.cost, c),
            t.waste ? "waste" : "keep",
          ])}
          lastIsChip
        />
      ) : null}

      {tab === "Ads" ? (
        <PwCard className="p-5 sm:p-6">
          {detail.ads.length === 0 ? (
            <p className="text-pw-ink-500 text-[15px]">No ad ran in this window.</p>
          ) : (
            <ul className="flex flex-col gap-4">
              {detail.ads.map((ad, i) => (
                <li
                  key={`${ad.ad_group}-${i}`}
                  className="border-pw-divider border-b pb-4 last:border-0 last:pb-0"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-[15px] font-semibold">
                      {ad.headlines.filter(Boolean).join(" · ") || ad.ad_group}
                    </p>
                    <Chip tone={ad.approval === "APPROVED" ? "good" : "bad"}>
                      {ad.approval === "APPROVED"
                        ? "Approved"
                        : ad.approval.toLowerCase().replace(/_/g, " ")}
                    </Chip>
                  </div>
                  <p className="text-pw-ink-500 mt-1 text-[14px]">
                    {ad.ad_group} · {ad.impressions.toLocaleString()} shown · {ad.clicks} clicks ·{" "}
                    {ad.click_rate}% clicked
                  </p>
                </li>
              ))}
            </ul>
          )}
        </PwCard>
      ) : null}

      {tab === "Change history" ? (
        <PwCard className="p-5 sm:p-6">
          <p className="text-pw-ink-500 text-[15px] leading-[24px]">
            Nothing, because PPCway has changed nothing in this account. When it can, every change
            will be listed here with what it was, who decided it — you, Otto or your expert — and a
            button to put it back for thirty days.
          </p>
        </PwCard>
      ) : null}
    </>
  );
}

function Table({
  head,
  rows,
  empty,
  lastIsChip,
}: {
  head: string[];
  rows: string[][];
  empty: string;
  lastIsChip?: boolean;
}) {
  if (rows.length === 0) {
    return (
      <PwCard className="p-6">
        <p className="text-pw-ink-500 text-[15px]">{empty}</p>
      </PwCard>
    );
  }
  return (
    <PwCard className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left">
        <thead>
          <tr className="border-pw-divider text-pw-ink-400 border-b text-[12px]">
            {head.map((h, i) => (
              <th
                key={h || i}
                className={cn(
                  "px-3 py-3 font-semibold",
                  i === 0 && "px-5 sm:px-6",
                  i > 0 && i < head.length - 1 && "text-right",
                )}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r} className="border-pw-divider hover:bg-pw-row-hover border-b last:border-0">
              {row.map((cell, i) => (
                <td
                  key={i}
                  className={cn(
                    "px-3 py-3 text-[15px]",
                    i === 0 && "max-w-[320px] truncate px-5 font-semibold sm:px-6",
                    i > 0 && i < row.length - 1 && "pw-num text-right",
                  )}
                >
                  {lastIsChip && i === row.length - 1 ? (
                    <Chip tone={cell === "waste" ? "bad" : "good"}>
                      {cell === "waste" ? "Waste" : "Keep"}
                    </Chip>
                  ) : (
                    cell
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </PwCard>
  );
}
