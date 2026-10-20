"use client";

import { useState } from "react";
import { money } from "@/components/pw/campaigns";
import { Chip, PwCard, Tile, Tiles } from "@/components/pw/shell";
import type { AdsDay } from "@/lib/ads";
import { cn } from "@/lib/cn";
import { LEARNING_DAYS, ago, learning } from "@/lib/when";

/*
  One campaign, opening underneath the list rather than on a page of its own, as
  the handoff draws it. Five tabs, and two sources behind them.

  What the campaign is made of, what it did day by day and what somebody changed
  in it are ours, out of the mirror. What each keyword and each ad did is
  Google's own reporting, read live. Either half can be missing without taking
  the page with it, and when Google's half is missing the tabs that need it say
  so rather than showing a zero that reads as "nothing happened".
*/
type Keyword = {
  keyword: string;
  match: string;
  status?: string;
  negative?: boolean;
  quality_score: number;
  bid?: number;
  ad_group?: string;
  clicks: number;
  leads: number;
  cost: number;
  cost_per_lead: number;
};
type Term = { term: string; clicks: number; leads: number; cost: number; waste: boolean };
type Ad = {
  ad_group: string;
  headlines: string[];
  descriptions?: string[];
  final_urls?: string[];
  approval: string;
  status: string;
  impressions: number;
  clicks: number;
  click_rate: number;
};
type Group = { ad_group_id: string; name: string; status: string; bid: number; gone?: boolean };
type Change = { kind: string; label: string; summary: string; when: string | null };

export type Detail = {
  read: boolean;
  trouble?: string;
  reconnect?: boolean;
  campaign_id: string;
  name: string;
  status: string;
  currency: string;
  days: number;
  leads: number;
  calls?: number;
  forms?: number;
  cost: number;
  clicks: number;
  impressions: number;
  budget: number;
  cost_per_lead: number;
  lead_rate: number;
  leads_before?: number;
  cost_before?: number;
  cost_per_lead_before?: number;
  lost_to_budget: number;
  lost_to_rank: number;
  impression_share: number;
  starts_at?: string;
  gone?: boolean;
  series?: AdsDay[];
  keywords: Keyword[];
  terms: Term[];
  ads: Ad[];
  groups?: Group[];
  history?: Change[];
  /** False when Google's own reporting could not be read just now. */
  metrics_read?: boolean;
};

const TABS = ["Overview", "Keywords", "Search terms", "Ads", "Change history"] as const;

/** "Against $42.10 in the 30 days before." Nothing, when there is no before. */
function against(before: number | undefined, days: number, say: (n: number) => string): string {
  return before ? `Against ${say(before)} in the ${days} days before.` : "";
}

export function CampaignDetail({ detail, onClose }: { detail: Detail; onClose?: () => void }) {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Overview");
  const c = detail.currency;
  const live = detail.metrics_read !== false;
  const day = learning(detail.starts_at);

  if (!detail.read) {
    return (
      <PwCard className="p-6 sm:p-8">
        <p className="text-pw-ink-500 text-[16px]">
          {detail.trouble ?? "We could not read this campaign."}
        </p>
      </PwCard>
    );
  }

  const words = detail.keywords ?? [];
  const positives = words.filter((k) => !k.negative);
  const negatives = words.filter((k) => k.negative);

  return (
    <PwCard className="overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-4 px-5 pt-5 pb-4 sm:px-6">
        <div className="min-w-0">
          <h2 className="display flex flex-wrap items-center gap-3 text-[22px] leading-[28px] font-semibold">
            {detail.name}
            <Chip tone={detail.status === "ENABLED" ? "good" : "neutral"}>
              {detail.status === "ENABLED" ? "Active" : "Paused"}
            </Chip>
            {day ? (
              <Chip tone="info">
                Learning · day {day} of {LEARNING_DAYS}
              </Chip>
            ) : null}
            {detail.gone ? <Chip tone="neutral">No longer in the account</Chip> : null}
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
            {name === "Change history" && (detail.history?.length ?? 0) > 0 ? (
              <span className="text-pw-ink-400 ml-[6px] text-[13px]">{detail.history?.length}</span>
            ) : null}
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
                note={
                  detail.cost_per_lead_before
                    ? `was ${money(detail.cost_per_lead_before, c)}`
                    : undefined
                }
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

            {against(detail.leads_before, detail.days, (n) => `${Math.round(n)} leads`) ? (
              <p className="text-pw-ink-500 text-[14px]">
                {against(detail.leads_before, detail.days, (n) => `${Math.round(n)} leads`)}{" "}
                {detail.cost_before ? `It spent ${money(detail.cost_before, c)} then.` : ""}
              </p>
            ) : null}

            <ByDay series={detail.series} currency={c} />

            {day ? (
              <div className="bg-pw-muted rounded-[14px] p-4">
                <p className="text-[15px] leading-[24px]">
                  <strong className="font-semibold">
                    This campaign is {day} {day === 1 ? "day" : "days"} old.
                  </strong>{" "}
                  Google needs about a week of a campaign&rsquo;s own data before its cost per lead
                  means anything, so nothing here is worth acting on yet.
                </p>
              </div>
            ) : null}

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

            {(detail.groups?.length ?? 0) > 1 ? (
              <p className="text-pw-ink-500 text-[14px]">
                {detail.groups?.length} ad groups: {detail.groups?.map((g) => g.name).join(", ")}.
              </p>
            ) : null}
          </>
        ) : null}

        {tab === "Keywords" ? (
          <>
            {!live ? <LiveMissing what="What each keyword cost and brought" /> : null}
            <Table
              empty={
                live
                  ? "No keyword spent anything in this window."
                  : "We hold no keywords for this campaign yet."
              }
              head={["Keyword", "Match", "Quality", "Clicks", "Leads", "Cost per lead"]}
              rows={positives.map((k) => [
                k.keyword,
                k.match,
                k.quality_score ? `${k.quality_score}/10` : "—",
                live ? String(k.clicks) : "—",
                live ? String(Math.round(k.leads)) : "—",
                live && k.cost_per_lead ? money(k.cost_per_lead, c) : "—",
              ])}
            />
            {negatives.length ? (
              <div>
                <h3 className="text-[15px] font-semibold">Words you have told Google to ignore</h3>
                <p className="text-pw-ink-500 mt-1 text-[14px] leading-[21px]">
                  {negatives.map((k) => k.keyword).join(" · ")}
                </p>
              </div>
            ) : null}
          </>
        ) : null}

        {tab === "Search terms" ? (
          live ? (
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
          ) : (
            <LiveMissing what="The searches people actually typed" />
          )
        ) : null}

        {tab === "Ads" ? (
          detail.ads.length === 0 ? (
            <p className="text-pw-ink-500 text-[15px]">
              {live ? "No ad ran in this window." : "We hold no ads for this campaign yet."}
            </p>
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
                    {ad.ad_group}
                    {live
                      ? ` · ${ad.impressions.toLocaleString()} shown · ${ad.clicks} clicks · ${ad.click_rate}% clicked`
                      : ""}
                  </p>
                  {ad.final_urls?.length ? (
                    <p className="text-pw-ink-400 mt-[2px] truncate text-[13px]">
                      Sends people to {ad.final_urls[0]}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          )
        ) : null}

        {tab === "Change history" ? <History history={detail.history ?? []} /> : null}
      </div>
    </PwCard>
  );
}

/*
  The campaign's own day-by-day, from the mirror. Bars rather than a line: a day
  with nothing in it should read as nothing.
*/
function ByDay({ series, currency }: { series: AdsDay[] | undefined; currency: string }) {
  const days = series ?? [];
  if (days.length < 2) return null;
  const peak = Math.max(...days.map((d) => d.cost), 0.01);
  const leads = days.reduce((n, d) => n + d.leads, 0);
  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-[15px] font-semibold">Day by day</h3>
        <p className="text-pw-ink-400 text-[12px]">
          Bar height is the day&rsquo;s spend; a dot marks a day that brought a lead.
        </p>
      </div>
      <div
        role="img"
        aria-label={`Spend by day over ${days.length} days, with ${Math.round(leads)} leads.`}
        className="mt-3 flex h-[120px] items-end gap-[2px]"
      >
        {days.map((d) => (
          <span key={d.date} className="flex h-full flex-1 flex-col justify-end gap-[3px]">
            <span
              aria-hidden
              className={cn(
                "mx-auto size-[5px] rounded-full",
                d.leads > 0 ? "bg-pw-good-ink" : "bg-transparent",
              )}
            />
            <span
              className="bg-pw-blue-light w-full rounded-t-[2px]"
              style={{ height: `${Math.max(2, (d.cost / peak) * 100)}%` }}
            />
          </span>
        ))}
      </div>
      <div className="text-pw-ink-400 mt-2 flex justify-between text-[12px]">
        <span>{days[0]?.date}</span>
        <span>
          {money(
            days.reduce((n, d) => n + d.cost, 0),
            currency,
          )}{" "}
          in all
        </span>
        <span>{days[days.length - 1]?.date}</span>
      </div>
    </div>
  );
}

/*
  The fifth tab. Everything in it was done by a person in Google Ads, not by us,
  which is the whole point of keeping it: the requirements ask that a change
  made outside PPCway is noticed and recorded as theirs.
*/
function History({ history }: { history: Change[] }) {
  if (history.length === 0) {
    return (
      <p className="text-pw-ink-500 text-[15px] leading-[24px]">
        Nothing has changed in this campaign since we started watching it, and PPCway has changed
        nothing at all. When somebody edits it in Google Ads, it is listed here with what moved and
        when we noticed. When PPCway can make changes, each of its own will appear here too, with a
        button to put it back for thirty days.
      </p>
    );
  }
  return (
    <>
      <p className="text-pw-ink-500 text-[14px] leading-[21px]">
        Everything here was done in Google Ads, not by PPCway. PPCway has changed nothing in this
        account.
      </p>
      <ul className="divide-pw-divider divide-y">
        {history.map((change, i) => (
          <li key={`${change.summary}-${i}`} className="flex flex-col gap-1 py-3">
            <p className="text-[15px] leading-[21px]">{change.summary}</p>
            <p className="text-pw-ink-400 text-[13px]">
              {change.label || change.kind}
              {change.when ? ` · noticed ${ago(change.when)}` : ""}
            </p>
          </li>
        ))}
      </ul>
    </>
  );
}

/** Google's own reporting is missing. Say which half, and why it matters. */
function LiveMissing({ what }: { what: string }) {
  return (
    <div className="border-pw-warn-border bg-pw-warn-bg rounded-[14px] border p-4">
      <p className="text-pw-warn-ink text-[14px] leading-[21px]">
        <strong className="font-bold">{what} could not be read just now.</strong> That part comes
        from Google&rsquo;s own reporting rather than our copy of your account, so it is missing
        rather than zero. Everything else on this page is ours and is up to date.
      </p>
    </div>
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
