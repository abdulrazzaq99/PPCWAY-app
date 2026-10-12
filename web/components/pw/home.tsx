import Link from "next/link";
import { ConnectButton } from "@/components/pw/connect-button";
import { Chip, Kpi, PwCard } from "@/components/pw/shell";
import { cn } from "@/lib/cn";

/*
  Dashboard home, from the client's handoff: "is it working, and what needs me?"
  in one view.

  Every figure here is read from the merchant's own Google Ads account. The
  parts of the design that need machinery we have not built — Otto's
  recommendations, what Otto did, the chat — say so in their own words rather
  than showing the handoff's sample numbers, which belong to a plumber in
  Toronto who does not exist.
*/
export type Summary = {
  read: boolean;
  trouble?: string;
  /** Google has ended the permission; the only way forward is to grant it again. */
  reconnect?: boolean;
  currency?: string;
  days?: number;
  leads?: number;
  calls?: number;
  forms?: number;
  cost?: number;
  cost_per_lead?: number;
  month_cost?: number;
  month_day?: number;
  month_days?: number;
  monthly_budget?: number;
  series?: { date: string; calls: number; forms: number; leads: number }[];
  campaigns?: {
    campaign_id: string;
    name: string;
    status: string;
    leads: number;
    cost: number;
    cost_per_lead: number;
  }[];
};

export type LatestAudit = { id: string; site: string; score: number | null; when: string } | null;

function money(amount: number, currency = ""): string {
  const sign = !currency || currency === "CAD" || currency === "USD" ? "$" : "";
  return `${sign}${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function Home({
  firstName,
  business,
  summary,
  audit,
  connected,
}: {
  firstName: string;
  business: string;
  summary: Summary;
  audit: LatestAudit;
  connected: boolean;
}) {
  const days = summary.days ?? 30;
  const currency = summary.currency ?? "";
  const onPace =
    summary.monthly_budget && summary.month_day && summary.month_days
      ? (summary.month_cost ?? 0) / summary.monthly_budget <= summary.month_day / summary.month_days
      : null;

  return (
    <>
      {summary.reconnect ? <GoneBanner /> : !connected ? <ConnectBanner /> : null}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi
          label="Leads"
          note={`Last ${days} days`}
          value={summary.read ? String(Math.round(summary.leads ?? 0)) : "—"}
          chip={
            summary.read && (summary.leads ?? 0) > 0 ? (
              <span className="text-pw-ink-500 text-[13px]">
                {Math.round(summary.calls ?? 0)} calls · {Math.round(summary.forms ?? 0)} forms
              </span>
            ) : null
          }
          foot={summary.read ? undefined : "Connect your account to count these."}
        />
        <Kpi
          label="Cost per lead"
          note={`Last ${days} days`}
          value={
            summary.read && (summary.cost_per_lead ?? 0) > 0
              ? money(summary.cost_per_lead ?? 0, currency)
              : "—"
          }
          foot={
            summary.read && (summary.leads ?? 0) === 0 && (summary.cost ?? 0) > 0
              ? `${money(summary.cost ?? 0, currency)} spent and nothing counted yet.`
              : undefined
          }
        />
        <Kpi
          label="This month"
          note={
            summary.read && summary.month_day
              ? `Day ${summary.month_day} of ${summary.month_days}`
              : undefined
          }
          value={summary.read ? money(summary.month_cost ?? 0, currency) : "—"}
          chip={
            onPace === null ? null : (
              <Chip tone={onPace ? "good" : "warn"}>{onPace ? "On pace" : "Ahead of pace"}</Chip>
            )
          }
          foot={
            summary.monthly_budget
              ? `of about ${money(summary.monthly_budget, currency)} in daily budgets`
              : undefined
          }
        />
        <ScoreCard audit={audit} />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.15fr_1fr]">
        <LeadsByDay summary={summary} />
        <NeedsYou connected={connected} />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.15fr_1fr]">
        <Campaigns summary={summary} currency={currency} days={days} />
        <WhatOttoDid />
      </div>

      <AskOtto firstName={firstName} business={business} />
    </>
  );
}

function ConnectBanner() {
  return (
    <div className="border-pw-warn-border bg-pw-warn-bg flex flex-wrap items-center justify-between gap-4 rounded-[14px] border px-5 py-4">
      <p className="text-pw-warn-ink text-[15px] leading-[22px]">
        <strong className="font-bold">Your Google Ads account is not connected yet.</strong> Connect
        it, read only, and this page fills with your own numbers.
      </p>
      <ConnectButton className="bg-pw-warn-ink rounded-[10px] px-4 py-2 text-[14px] font-semibold text-white" />
    </div>
  );
}

function GoneBanner() {
  return (
    <div className="border-pw-warn-border bg-pw-warn-bg flex flex-wrap items-center justify-between gap-4 rounded-[14px] border px-5 py-4">
      <p className="text-pw-warn-ink max-w-[760px] text-[15px] leading-[22px]">
        <strong className="font-bold">Google has ended the permission for your account.</strong>{" "}
        Connect again and this page fills back in. Nothing of yours was changed, and your campaigns
        are untouched.
      </p>
      <ConnectButton
        label="Connect again"
        className="bg-pw-warn-ink rounded-[10px] px-4 py-2 text-[14px] font-semibold text-white"
      />
    </div>
  );
}

function ScoreCard({ audit }: { audit: LatestAudit }) {
  const score = audit?.score ?? null;
  const ring = score === null ? 0 : score * 3.6;
  const colour =
    score === null ? "#C9C4D9" : score >= 75 ? "#16A34A" : score >= 55 ? "#B45309" : "#DC2626";
  return (
    <PwCard className="flex items-center gap-4 p-5">
      <div
        aria-hidden
        className="flex size-[76px] shrink-0 items-center justify-center rounded-full"
        style={{ background: `conic-gradient(${colour} ${ring}deg, #F0EEEA 0)` }}
      >
        <span className="bg-pw-card pw-num flex size-[60px] items-center justify-center rounded-full text-[22px] font-semibold">
          {score ?? "—"}
        </span>
      </div>
      <div className="min-w-0">
        <p className="text-[14px] leading-[18px] font-semibold">Visibility Score</p>
        {audit ? (
          <>
            <p className="text-pw-ink-500 mt-1 truncate text-[13px] leading-[17px]">
              {audit.site.replace(/^https?:\/\//, "").replace(/\/$/, "")}
            </p>
            <Link
              href={`/audit/${audit.id}`}
              className="text-pw-blue mt-1 inline-block text-[13px] font-semibold"
            >
              Open the audit →
            </Link>
          </>
        ) : (
          <Link href="/audit" className="text-pw-blue mt-1 inline-block text-[13px] font-semibold">
            Run your free audit →
          </Link>
        )}
      </div>
    </PwCard>
  );
}

function LeadsByDay({ summary }: { summary: Summary }) {
  const series = summary.series ?? [];
  const peak = Math.max(1, ...series.map((d) => d.leads));
  const any = series.some((d) => d.leads > 0);
  return (
    <PwCard className="p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-[17px] leading-[22px] font-semibold">Leads by day</h2>
        <p className="text-pw-ink-500 flex items-center gap-3 text-[12px]">
          <span className="flex items-center gap-[6px]">
            <span aria-hidden className="bg-pw-blue size-[10px] rounded-[3px]" /> Calls
          </span>
          <span className="flex items-center gap-[6px]">
            <span aria-hidden className="bg-pw-blue-light size-[10px] rounded-[3px]" /> Forms
          </span>
        </p>
      </div>

      {!summary.read ? (
        <Empty>Your day-by-day leads appear here once your account is connected.</Empty>
      ) : !any ? (
        <Empty>
          Nothing has been counted in this window. If your ads are running, the conversion tracking
          may not be set up — the audit checks that.
        </Empty>
      ) : (
        <>
          <div
            role="img"
            aria-label={`Leads by day: ${Math.round(summary.leads ?? 0)} in ${summary.days} days.`}
            className="mt-5 flex h-[190px] items-end gap-[3px]"
          >
            {series.map((day) => (
              <span key={day.date} className="flex h-full flex-1 flex-col justify-end">
                <span
                  className="bg-pw-blue-light w-full rounded-t-[3px]"
                  style={{ height: `${(day.forms / peak) * 100}%` }}
                />
                <span
                  className="bg-pw-blue w-full"
                  style={{ height: `${(day.calls / peak) * 100}%` }}
                />
              </span>
            ))}
          </div>
          <div className="text-pw-ink-400 mt-2 flex justify-between text-[12px]">
            <span>{series[0]?.date}</span>
            <span>{series[series.length - 1]?.date}</span>
          </div>
        </>
      )}
    </PwCard>
  );
}

function NeedsYou({ connected }: { connected: boolean }) {
  return (
    <PwCard className="p-5 sm:p-6">
      <h2 className="text-[17px] leading-[22px] font-semibold">Needs you</h2>
      <Empty>
        {connected
          ? "Otto is not watching this account yet. When it is, the changes worth making appear here for you to approve, one tap each, and nothing is applied without your yes."
          : "Once your account is connected and Otto starts watching it, the changes worth making appear here for your approval."}
      </Empty>
    </PwCard>
  );
}

function Campaigns({
  summary,
  currency,
  days,
}: {
  summary: Summary;
  currency: string;
  days: number;
}) {
  const rows = summary.campaigns ?? [];
  return (
    <PwCard className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-5 sm:px-6">
        <h2 className="text-[17px] leading-[22px] font-semibold">Campaigns</h2>
        {rows.length ? (
          <Link href="/campaigns" className="text-pw-blue text-[14px] font-semibold">
            All campaigns →
          </Link>
        ) : null}
      </div>
      {rows.length === 0 ? (
        <div className="px-5 pb-6 sm:px-6">
          <Empty>
            {summary.read
              ? "This account has no campaigns running in this window."
              : "Your campaigns appear here once your account is connected."}
          </Empty>
        </div>
      ) : (
        <table className="w-full text-left">
          <thead>
            <tr className="border-pw-divider text-pw-ink-400 border-y text-[12px]">
              <th className="px-5 py-2 font-semibold sm:px-6">Campaign</th>
              <th className="px-3 py-2 text-right font-semibold">Leads</th>
              <th className="px-3 py-2 text-right font-semibold">Cost per lead</th>
              <th className="px-5 py-2 font-semibold sm:px-6">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 6).map((row) => (
              <tr
                key={row.campaign_id}
                className="border-pw-divider hover:bg-pw-row-hover border-b last:border-0"
              >
                <td className="max-w-[220px] truncate px-5 py-3 text-[15px] font-semibold sm:px-6">
                  {row.name}
                </td>
                <td className="pw-num px-3 py-3 text-right text-[15px]">{Math.round(row.leads)}</td>
                <td className="pw-num px-3 py-3 text-right text-[15px]">
                  {row.cost_per_lead > 0 ? money(row.cost_per_lead, currency) : "—"}
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
      {rows.length ? (
        <p className="text-pw-ink-400 px-5 pt-3 pb-5 text-[12px] sm:px-6">
          Last {days} days, read from your Google Ads account.
        </p>
      ) : null}
    </PwCard>
  );
}

function WhatOttoDid() {
  return (
    <PwCard tone="night" className="p-5 sm:p-6">
      <h2 className="text-[17px] leading-[22px] font-semibold">What Otto did</h2>
      <p className="text-pw-night-muted mt-3 text-[15px] leading-[23px]">
        Nothing yet, and nothing will happen without your say-so. When Otto starts work, every
        change it makes is listed here with what it was, why, and a button to undo it for thirty
        days.
      </p>
    </PwCard>
  );
}

function AskOtto({ firstName, business }: { firstName: string; business: string }) {
  return (
    <PwCard className="p-5 sm:p-6">
      <h2 className="text-[17px] leading-[22px] font-semibold">Ask Otto about your campaigns</h2>
      <p className="text-pw-ink-500 mt-2 text-[15px] leading-[23px]">
        Otto is not switched on yet. When it is, {firstName}, you will be able to ask plain
        questions about {business} here — why calls dropped on Sunday, which service brings the
        cheapest leads — and get answers from your own numbers.
      </p>
    </PwCard>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <p
      className={cn(
        "text-pw-ink-500 border-pw-divider mt-4 rounded-[12px] border border-dashed px-4 py-5 text-[14px] leading-[22px]",
      )}
    >
      {children}
    </p>
  );
}
