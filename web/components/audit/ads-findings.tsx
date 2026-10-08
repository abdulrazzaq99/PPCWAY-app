"use client";

import { CheckCircle, LockSimpleOpen, WarningCircle } from "@phosphor-icons/react/dist/ssr";
import { Card } from "@/components/audit/shell";

/*
  The four checks that were locked, once the merchant has connected their account
  and said which one to read. Real figures only: a check Google refused says so in
  its own row rather than showing a zero that reads like good news.

  A sentence before a number, a number before a list.
*/
export type AdsReading = {
  customer_id: string;
  window_days: number;
  spend: {
    read: boolean;
    trouble: string;
    cost: number;
    clicks: number;
    impressions: number;
    conversions: number;
    currency: string;
    cost_per_click: number;
    cost_per_conversion: number;
  };
  wasted: { read: boolean; trouble: string; cost: number; terms: Wasted[] };
  keywords: { read: boolean; trouble: string; rows: Weak[] };
  share: { read: boolean; trouble: string; rows: Share[] };
  rejected: { read: boolean; trouble: string; rows: Rejected[] };
};
type Wasted = { term: string; cost: number; clicks: number };
type Weak = { keyword: string; quality_score: number; cost: number; clicks: number };
type Share = {
  campaign: string;
  cost: number;
  lost_to_budget: number;
  lost_to_rank: number;
  impression_share: number;
};
type Rejected = { campaign: string; ad_group: string; status: string };

function money(amount: number, currency: string): string {
  const sign = currency === "CAD" || currency === "USD" || !currency ? "$" : "";
  return `${sign}${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function Row({
  title,
  verdict,
  read,
  trouble,
  children,
}: {
  title: string;
  verdict: string;
  read: boolean;
  trouble: string;
  children?: React.ReactNode;
}) {
  const bad = read && verdict.startsWith("!");
  return (
    <li className="px-5 py-5 sm:px-7">
      <div className="flex items-start gap-4">
        <span
          aria-hidden
          className={`mt-[2px] flex size-[26px] shrink-0 items-center justify-center rounded-full text-white ${
            !read ? "bg-faint" : bad ? "bg-red" : "bg-green"
          }`}
        >
          {!read ? (
            <WarningCircle size={14} weight="bold" />
          ) : bad ? (
            <WarningCircle size={14} weight="bold" />
          ) : (
            <CheckCircle size={14} weight="bold" />
          )}
        </span>
        <div className="min-w-0">
          <p className="text-[16px] leading-[21px] font-bold">{title}</p>
          <p className="text-muted mt-1 text-[15px] leading-[22px]">
            {read ? verdict.replace(/^!/, "") : trouble}
          </p>
          {read ? children : null}
        </div>
      </div>
    </li>
  );
}

function Lines({ rows }: { rows: string[] }) {
  if (rows.length === 0) return null;
  return (
    <ul className="divide-line-soft border-line-soft mt-3 divide-y border-t">
      {rows.map((row) => (
        <li key={row} className="py-2 text-[15px] leading-[21px] font-semibold">
          {row}
        </li>
      ))}
    </ul>
  );
}

export function AdsFindings({ ads }: { ads: AdsReading }) {
  const currency = ads.spend.currency;
  const spent = money(ads.spend.cost, currency);
  const wastedShare = ads.spend.cost > 0 ? Math.round((ads.wasted.cost / ads.spend.cost) * 100) : 0;
  const worstShare = [...ads.share.rows].sort((a, b) => b.lost_to_budget - a.lost_to_budget)[0];
  const weakCost = ads.keywords.rows.reduce((sum, row) => sum + row.cost, 0);

  return (
    <section className="mt-8">
      <Card className="overflow-hidden">
        <div className="border-line-soft border-b px-5 py-5 sm:px-7">
          <p className="text-brand flex items-center gap-2 text-[13px] leading-4 font-semibold tracking-[0.08em] uppercase">
            <LockSimpleOpen aria-hidden size={14} weight="bold" />
            Open, from your own account
          </p>
          <h2 className="mt-2 text-[20px] leading-[26px] font-semibold">
            {!ads.spend.read
              ? "We could not read what your account spent."
              : ads.spend.cost > 0
                ? `You spent ${spent} on Google Ads in the last ${ads.window_days} days.`
                : `Your account shows no spend in the last ${ads.window_days} days.`}
          </h2>
          <p className="text-muted mt-1 max-w-[680px] text-[15px] leading-[23px]">
            {!ads.spend.read
              ? ads.spend.trouble
              : ads.spend.clicks > 0
                ? `That bought ${ads.spend.clicks.toLocaleString()} clicks at ${money(ads.spend.cost_per_click, currency)} each${
                    ads.spend.conversions > 0
                      ? `, and ${ads.spend.conversions} enquiries at ${money(ads.spend.cost_per_conversion, currency)} each.`
                      : ", and no enquiries Google could count."
                  }`
                : "Nothing was clicked, so there is nothing yet to judge the spending by."}
          </p>
        </div>

        <ul className="divide-line-soft divide-y">
          <Row
            title="Wasted spend on search terms"
            read={ads.wasted.read}
            trouble={ads.wasted.trouble}
            verdict={
              ads.wasted.cost > 0
                ? `!${money(ads.wasted.cost, currency)} went to ${ads.wasted.terms.length} searches that brought no enquiry${
                    wastedShare > 0 ? `, which is ${wastedShare}% of what you spent.` : "."
                  }`
                : "Every search that cost you money brought an enquiry back."
            }
          >
            <Lines
              rows={ads.wasted.terms
                .slice(0, 5)
                .map(
                  (term) =>
                    `${term.term} · ${money(term.cost, currency)} · ${term.clicks} ${term.clicks === 1 ? "click" : "clicks"}`,
                )}
            />
          </Row>

          <Row
            title="Quality Score by keyword"
            read={ads.keywords.read}
            trouble={ads.keywords.trouble}
            verdict={
              ads.keywords.rows.length > 0
                ? `!Google scores ${ads.keywords.rows.length} of your keywords at five or less, and they took ${money(weakCost, currency)}. A low score means you pay more than your competitors for the same click.`
                : "Google scores none of your keywords poorly."
            }
          >
            <Lines
              rows={ads.keywords.rows
                .slice(0, 5)
                .map(
                  (row) =>
                    `${row.keyword} · scored ${row.quality_score} of 10 · ${money(row.cost, currency)}`,
                )}
            />
          </Row>

          <Row
            title="Budget lost to impression share"
            read={ads.share.read}
            trouble={ads.share.trouble}
            verdict={
              worstShare && worstShare.lost_to_budget >= 5
                ? `!${worstShare.campaign} missed ${worstShare.lost_to_budget}% of its searches because the budget ran out, and ${worstShare.lost_to_rank}% because the ad ranked too low.`
                : worstShare
                  ? `Your budget is keeping up: ${worstShare.campaign} shows on ${worstShare.impression_share}% of its searches.`
                  : "No campaign ran in this window."
            }
          >
            <Lines
              rows={ads.share.rows
                .slice(0, 4)
                .map(
                  (row) =>
                    `${row.campaign} · shown on ${row.impression_share}% · ${row.lost_to_budget}% lost to budget`,
                )}
            />
          </Row>

          <Row
            title="Ad disapprovals and policy issues"
            read={ads.rejected.read}
            trouble={ads.rejected.trouble}
            verdict={
              ads.rejected.rows.length > 0
                ? `!${ads.rejected.rows.length} of your ads are disapproved, so they are not being shown at all.`
                : "Google is showing every one of your ads."
            }
          >
            <Lines
              rows={ads.rejected.rows
                .slice(0, 5)
                .map((row) => `${row.campaign} · ${row.ad_group} · ${row.status.toLowerCase()}`)}
            />
          </Row>
        </ul>
      </Card>
    </section>
  );
}
