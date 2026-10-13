"use client";

import { useState } from "react";
import { money } from "@/components/pw/campaigns";
import { Chip, PwCard, Tile, Tiles } from "@/components/pw/shell";
import { cn } from "@/lib/cn";

/*
  One campaign, opening underneath the list rather than on a page of its own, as
  the handoff draws it. Five tabs; four of them are read from the account today.

  Change history is empty on purpose and says why. It waits on the change log,
  which is the first thing built when PPCway starts writing — and until then an
  empty history is the truthful answer: we have changed nothing.
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

export function CampaignDetail({ detail, onClose }: { detail: Detail; onClose?: () => void }) {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Overview");
  const c = detail.currency;

  if (!detail.read) {
    return (
      <PwCard className="p-6 sm:p-8">
        <p className="text-pw-ink-500 text-[16px]">
          {detail.trouble ?? "We could not read this campaign."}
        </p>
      </PwCard>
    );
  }

  return (
    <PwCard className="overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-4 px-5 pt-5 pb-4 sm:px-6">
        <div className="min-w-0">
          <h2 className="display flex flex-wrap items-center gap-3 text-[22px] leading-[28px] font-semibold">
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
        {onClose ? (
          <button
            type="button"
            onClick={onClose}
            className="text-pw-ink-500 hover:text-pw-ink text-[14px] font-semibold"
          >
            Close
          </button>
        ) : null}
      </div>

      <div className="border-pw-divider flex gap-5 overflow-x-auto border-b px-5 sm:px-6">
        {TABS.map((name) => (
          <button
            key={name}
            type="button"
            onClick={() => setTab(name)}
            className={cn(
              "-mb-px border-b-2 pb-3 text-[15px] font-semibold whitespace-nowrap",
              tab === name
                ? "border-pw-ink text-pw-ink"
                : "text-pw-ink-500 hover:text-pw-ink border-transparent",
            )}
          >
            {name}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-4 p-5 sm:p-6">
        {tab === "Overview" ? (
          <>
            <Tiles>
              <Tile label="Leads" value={String(Math.round(detail.leads))} />
              <Tile
                label="Cost per lead"
                value={detail.cost_per_lead ? money(detail.cost_per_lead, c) : "—"}
              />
              <Tile
                label="Spend"
                value={money(detail.cost, c)}
                note={detail.budget ? `${money(detail.budget, c)} a day` : undefined}
              />
              <Tile label="Clicks" value={detail.clicks.toLocaleString()} />
              <Tile
                label="Lead rate"
                value={detail.clicks ? `${detail.lead_rate}%` : "—"}
                note="of clicks became leads"
              />
              <Tile
                label="Search share"
                value={detail.impression_share ? `${detail.impression_share}%` : "—"}
                note={
                  detail.lost_to_budget >= 5
                    ? `Lost ${detail.lost_to_budget}% to budget`
                    : detail.lost_to_rank >= 20
                      ? `Lost ${detail.lost_to_rank}% to rank`
                      : undefined
                }
                tone={detail.lost_to_budget >= 5 || detail.lost_to_rank >= 20 ? "warn" : undefined}
              />
            </Tiles>

            {detail.lost_to_rank >= 20 ? (
              <div className="bg-pw-blue-tint-2 rounded-[14px] p-4">
                <p className="text-[15px] leading-[24px]">
                  <strong className="font-semibold">
                    This campaign misses {detail.lost_to_rank}% of its searches because the ad ranks
                    too low, not because the budget runs out.
                  </strong>{" "}
                  More money would not fix that; better keywords, ads and landing pages would. The
                  website audit checks the last of those.
                </p>
              </div>
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
          detail.ads.length === 0 ? (
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
          )
        ) : null}

        {tab === "Change history" ? (
          <p className="text-pw-ink-500 text-[15px] leading-[24px]">
            Nothing, because PPCway has changed nothing in this account. When it can, every change
            will be listed here with what it was, who decided it — you, Otto or your expert — and a
            button to put it back for thirty days.
          </p>
        ) : null}
      </div>
    </PwCard>
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
    return <p className="text-pw-ink-500 text-[15px]">{empty}</p>;
  }
  return (
    <div className="border-pw-border overflow-x-auto rounded-[14px] border">
      <table className="w-full min-w-[640px] text-left">
        <thead>
          <tr className="border-pw-divider text-pw-ink-500 border-b text-[13px]">
            {head.map((h, i) => (
              <th
                key={h || i}
                className={cn(
                  "px-3 py-3 font-semibold",
                  i === 0 && "pl-4",
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
                    i === 0 && "max-w-[320px] truncate pl-4 font-semibold",
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
    </div>
  );
}
