"use client";

import { useEffect, useState } from "react";
import { CampaignDetail, type Detail, type Suggestions } from "@/components/pw/campaign-detail";
import {
  CampaignStatus,
  deletedWords as deletedNote,
  isDeleted,
} from "@/components/pw/campaign-status";
import {
  Figures,
  LeadsByDay,
  MoneyAndLeads,
  NeedsLine,
  SetAside,
  findingOf,
} from "@/components/pw/campaign-overview";
import { Drafts, type DraftRow } from "@/components/pw/create/drafts";
import { Chip, Pill, PillGroup, PwCard } from "@/components/pw/shell";
import { Sparkline } from "@/components/pw/sparkline";
import type { AdsSummary } from "@/lib/ads";
import type { Inbox } from "@/lib/otto";
import { cn } from "@/lib/cn";
import { LEARNING_DAYS, learning } from "@/lib/when";

/*
  Campaigns. The screen answers one question before it lists anything: which
  campaigns are earning their money? So it opens with the finding in a
  sentence, four figures against the period before, "money in, leads out" --
  each campaign's share of the spend above its share of the leads -- and leads
  a day. Then the table, with a leads trend per row and the chosen campaign
  opening underneath rather than on a page of its own, so picking a row and
  reading its keywords is one movement and the list stays in sight.

  Every figure is read from the merchant's own Google Ads account.
*/
type Summary = AdsSummary;

const FILTERS = ["All", "Active", "Paused", "Deleted"] as const;

export function money(amount: number, currency = ""): string {
  const sign = !currency || currency === "CAD" || currency === "USD" ? "$" : "";
  return `${sign}${amount.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function CampaignList({
  initial,
  days: initialDays,
  drafts = [],
}: {
  initial: Summary;
  days: number;
  /** Campaigns started and not published, shown beside the list. */
  drafts?: DraftRow[];
}) {
  const [summary, setSummary] = useState(initial);
  const [days, setDays] = useState(initialDays);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("All");
  const [find, setFind] = useState("");
  const [chosen, setChosen] = useState<string>("");
  const [detail, setDetail] = useState<Detail | null>(null);
  const [asks, setAsks] = useState(0);
  // Otto's cards for the chosen campaign, with the campaign they were asked
  // for, so a slow answer for the last row is never shown under the next.
  const [otto, setOtto] = useState<(Suggestions & { campaign: string }) | null>(null);
  const [ottoAsks, setOttoAsks] = useState(0);

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

  useEffect(() => {
    if (!chosen) return;
    let stop = false;
    const missed = "Otto could not be reached just now.";
    fetch(`/api/otto/inbox?campaign=${encodeURIComponent(chosen)}`, { cache: "no-store" })
      .then(async (r) => {
        const said = (await r.json().catch(() => ({}))) as Inbox & { error?: string };
        if (stop) return;
        setOtto(
          r.ok
            ? { campaign: chosen, inbox: said, trouble: "" }
            : { campaign: chosen, inbox: null, trouble: said.error ?? missed },
        );
      })
      .catch(() => {
        if (!stop) setOtto({ campaign: chosen, inbox: null, trouble: missed });
      });
    return () => {
      stop = true;
    };
  }, [chosen, ottoAsks]);

  // A campaign deleted in Google Ads is neither active nor paused: it is
  // listed only for the days it spent money in, so the totals add up.
  const deleted = (summary.campaigns ?? []).filter(isDeleted).length;
  const rows = (summary.campaigns ?? []).filter((row) => {
    const gone = isDeleted(row);
    const active = row.status === "ENABLED" && !gone;
    if (filter === "Active" && !active) return false;
    if (filter === "Paused" && (active || gone)) return false;
    if (filter === "Deleted" && !gone) return false;
    return row.name.toLowerCase().includes(find.trim().toLowerCase());
  });
  const currency = summary.currency ?? "";

  const read = summary.read && (summary.campaigns?.length ?? 0) > 0;

  return (
    <>
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <p className="max-w-[760px] text-[18px] leading-[26px] font-semibold">
          {read ? findingOf(summary) : "Your campaigns, from your own Google Ads account."}
        </p>
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
      </div>

      {read ? (
        <>
          <NeedsLine needs={summary.needs} />
          <Figures summary={summary} />
        </>
      ) : null}

      {/*
        Campaigns first, as the owner chose for this page: the list is what a
        merchant opens it for. Drafts sit beside it on a wide screen instead
        of across the top, and under it on a narrow one; the charts that
        explain the totals come after.
      */}
      <div
        className={cn(
          "grid items-start gap-4",
          // The table needs about 880px, so the panel goes beside it only on
          // a wide screen; below that it sits under the list as a grid.
          drafts.length > 0 && "2xl:grid-cols-[minmax(0,1fr)_320px]",
        )}
      >
        <div className="flex min-w-0 flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-[17px] leading-[22px] font-semibold">Every campaign</h2>
              <PillGroup>
                {FILTERS.filter((name) => name !== "Deleted" || deleted > 0).map((name) => (
                  <Pill key={name} active={filter === name} onClick={() => setFilter(name)}>
                    {name}
                    {name === "All" && summary.campaigns ? ` ${summary.campaigns.length}` : ""}
                  </Pill>
                ))}
              </PillGroup>
            </div>
            <input
              value={find}
              onChange={(e) => setFind(e.target.value)}
              placeholder="Find a campaign"
              aria-label="Find a campaign"
              className="border-pw-border-input bg-pw-card h-[42px] w-full rounded-full border px-4 text-[14px] sm:w-[240px]"
            />
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
                    <th className="py-3 pr-2 pl-4 font-semibold sm:px-6">Campaign</th>
                    <th className="hidden px-3 py-3 font-semibold sm:table-cell">Status</th>
                    <th className="hidden px-3 py-3 text-right font-semibold md:table-cell">
                      Budget a day
                    </th>
                    <th className="px-2 py-3 text-right font-semibold sm:px-3">Spend</th>
                    <th className="px-2 py-3 text-right font-semibold sm:px-3">Leads</th>
                    <th className="py-3 pr-4 pl-2 text-right font-semibold sm:px-3">
                      Cost per lead
                    </th>
                    <th className="hidden px-5 py-3 font-semibold sm:px-6 lg:table-cell">
                      Leads a day
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => {
                    const here = chosen === row.campaign_id;
                    // Google's bidding needs about a week of a campaign's own data
                    // before its cost per lead means anything. Saying so is the
                    // difference between a judgement and a guess.
                    const day = isDeleted(row) ? 0 : learning(row.starts_at);
                    const deletedWords = deletedNote(row);
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
                            "max-w-[150px] py-3 pr-2 pl-4 text-[15px] font-semibold sm:max-w-[360px] sm:pl-6",
                            here && "border-pw-blue border-l-[3px] pl-[17px] sm:pl-[21px]",
                          )}
                        >
                          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
                            {/* Two lines rather than an ellipsis: Google Ads names
                            run long, and the end is often the part that tells
                            two campaigns apart. */}
                            <span className="line-clamp-2" title={row.name}>
                              {row.name}
                            </span>
                            {day ? (
                              <Chip tone="info">
                                Learning · day {day} of {LEARNING_DAYS}
                              </Chip>
                            ) : null}
                            {isDeleted(row) ? (
                              // The status column is hidden on a phone, so the
                              // word goes beside the name there instead.
                              <span className="sm:hidden" title={deletedWords}>
                                <Chip tone="neutral">Deleted</Chip>
                              </span>
                            ) : null}
                          </span>
                        </td>
                        <td className="hidden px-3 py-3 sm:table-cell">
                          <CampaignStatus row={row} />
                        </td>
                        <td className="pw-num hidden px-3 py-3 text-right text-[15px] md:table-cell">
                          {isDeleted(row) ? (
                            <span className="text-pw-ink-400">None</span>
                          ) : row.budget ? (
                            money(row.budget, currency)
                          ) : (
                            "None"
                          )}
                        </td>
                        <td className="pw-num px-2 py-3 text-right text-[15px] sm:px-3">
                          {money(row.cost, currency)}
                        </td>
                        <td className="pw-num px-2 py-3 text-right text-[15px] sm:px-3">
                          {Math.round(row.leads)}
                        </td>
                        <td className="pw-num py-3 pr-4 pl-2 text-right text-[15px] sm:px-3">
                          {row.cost_per_lead ? money(row.cost_per_lead, currency) : "—"}
                        </td>
                        <td className="hidden px-5 py-3 sm:px-6 lg:table-cell">
                          {/* One bar a day, from our own mirror. A trend answers
                          "which way is this going", which a share of spend
                          never could. */}
                          <Sparkline
                            days={row.days}
                            by="leads"
                            label={`${Math.round(row.leads)} leads over ${days} days in ${row.name}`}
                          />
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
              <CampaignDetail
                detail={detail}
                onClose={() => setChosen("")}
                suggestions={otto && otto.campaign === chosen ? otto : undefined}
                onAnswered={() => setOttoAsks((n) => n + 1)}
              />
            ) : (
              <PwCard className="p-6">
                <p className="text-pw-ink-500 text-[15px]">Reading that campaign…</p>
              </PwCard>
            )
          ) : null}

          <p className="text-pw-ink-500 max-w-[860px] text-[13px] leading-[20px]">
            {deleted > 0
              ? `${deleted === 1 ? "One campaign was" : `${deleted} campaigns were`} deleted in Google Ads. ${deleted === 1 ? "It stays" : "They stay"} in this list for the days ${deleted === 1 ? "it" : "they"} spent money in, so the totals still add up. `
              : ""}
            Pausing, resuming and budget changes are not switched on yet. When they are, each one
            becomes a change you approve, with the before and after shown and thirty days to undo
            it.
          </p>
        </div>

        {drafts.length > 0 ? (
          <aside className="flex flex-col gap-4 2xl:sticky 2xl:top-6">
            <Drafts drafts={drafts} />
          </aside>
        ) : null}
      </div>

      {read ? (
        <>
          <div className="mt-2 grid items-stretch gap-4 lg:grid-cols-12">
            <div className="lg:col-span-7">
              <MoneyAndLeads summary={summary} />
            </div>
            <div className="flex lg:col-span-5 [&>section]:flex-1">
              <LeadsByDay series={summary.series ?? []} />
            </div>
          </div>
          <SetAside summary={summary} />
        </>
      ) : null}
    </>
  );
}
