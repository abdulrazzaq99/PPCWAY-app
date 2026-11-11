import { ArrowRight, CaretDown, ClockCounterClockwise } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import type { ReactNode } from "react";
import { Chip, PwCard } from "@/components/pw/shell";
import { cn } from "@/lib/cn";
import { moneyOf } from "@/lib/money";
import {
  CHANGE_STATUS,
  type CampaignShare,
  type DayBar,
  VERDICT_TONES,
  VERDICT_WORDS,
  afterTheSentence,
  busiestDay,
  campaignShares,
  changeDay,
  changesSentence,
  compared,
  dayBars,
  dayMonth,
  figuresByKey,
  freshness,
  periodWords,
  sharePercent,
  showFigure,
  weekdayDayMonth,
  whereFrom,
} from "@/lib/report-view";
import type { Figure, ReportChange, ReportSaid } from "@/lib/reports";

/*
  The report, as the app shows it and as a shared link shows it: one component,
  because the owner and the accountant they send it to should read the same page.

  It reads like a statement, top to bottom:

  - The period in one sentence, large, beside the three figures that matter:
    leads, what each one cost, and what was spent. Each says what it was before
    and whether the move is real, in words rather than an arrow. Eleven leads
    and then eight is not a thirty per cent collapse.
  - The quieter figures in one strip.
  - Day by day, as two charts on one time line, leads above spend, so a day
    that cost money and brought nothing is seen at a glance.
  - Where the leads came from, each campaign's share of the spend beside its
    share of the leads.
  - What PPCWay changed in those dates, from the log written before each change.
  - What the words mean, folded away until somebody asks.

  Server-rendered throughout: nothing here needs the browser, so nothing here
  can fail to hydrate.
*/

/* The report's display face: the brand's Outfit, for the sentence and the figures. */
const DISPLAY = "font-(family-name:--font-outfit) tracking-[-0.015em]";

export function Report({ said, share }: { said: ReportSaid; share?: ReactNode }) {
  const currency = said.currency ?? "";
  const days = said.days ?? 30;
  const shares = campaignShares(said.campaigns);
  return (
    <>
      <Summary said={said} rows={shares} />
      <OtherFigures said={said} />
      <DayByDay bars={dayBars(said.series)} currency={currency} said={said} />
      <WhereFrom rows={shares} currency={currency} />
      {said.changes ? <Changes said={said} /> : null}
      {share ? (
        <PwCard className="p-6 sm:p-8">
          <h2 className="text-[17px] leading-[22px] font-semibold">Send it to someone</h2>
          <p className="text-pw-ink-600 mt-1.5 max-w-[62ch] text-[15px] leading-[23px]">
            A link to this report that needs no login: for an accountant, a partner, anyone who asks
            what the advertising costs. It shows the last {days} days as they stand on the day it is
            opened, and stops working after a fortnight.
          </p>
          <div className="mt-4">{share}</div>
        </PwCard>
      ) : null}
      <Words said={said} />
    </>
  );
}

/* ---------- the statement ---------- */

function Summary({ said, rows }: { said: ReportSaid; rows: CampaignShare[] }) {
  const currency = said.currency ?? "";
  const days = said.days ?? 30;
  const f = figuresByKey(said);
  const headline = [f.leads, f.cost_per_lead, f.cost].filter((x): x is Figure => Boolean(x));
  return (
    <PwCard className="overflow-hidden">
      <div className="grid lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <div className="flex flex-col justify-between gap-8 p-6 sm:p-8">
          <div>
            <p className="text-pw-ink-500 text-[14px] leading-[20px]">
              {periodWords(said.starts_on ?? "", said.ends_on ?? "")}, the last {days} days
            </p>
            <p
              className={cn(
                DISPLAY,
                "text-pw-ink mt-3 max-w-[26ch] text-[27px] leading-[35px] font-medium text-balance sm:text-[34px] sm:leading-[43px]",
              )}
            >
              {said.sentence}
            </p>
            {afterTheSentence(said, rows) ? (
              <p className="text-pw-ink-600 mt-5 max-w-[54ch] text-[16px] leading-[25px]">
                {afterTheSentence(said, rows)}
              </p>
            ) : null}
          </div>
          <p className="text-pw-ink-500 flex max-w-[56ch] items-start gap-2.5 text-[13px] leading-[20px]">
            <ClockCounterClockwise size={16} weight="bold" className="mt-[2px] shrink-0" />
            <span>{freshness(said)}</span>
          </p>
        </div>
        <dl className="border-pw-border divide-pw-border bg-pw-ground/45 divide-y border-t lg:border-t-0 lg:border-l">
          {headline.map((figure) => (
            <div key={figure.key} className="px-6 py-5 sm:px-8">
              <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5">
                <dt className="text-pw-ink-600 text-[14px] leading-[20px] font-medium">
                  {figure.label}
                </dt>
                <Verdict figure={figure} />
              </div>
              <dd>
                <p
                  className={cn(
                    DISPLAY,
                    "pw-num text-pw-ink mt-1 text-[34px] leading-[42px] font-semibold",
                  )}
                >
                  {showFigure(figure.value, figure.kind, currency)}
                </p>
                <p className="text-pw-ink-500 mt-0.5 text-[13px] leading-[19px]">
                  {compared(figure, days, currency)}
                </p>
              </dd>
            </div>
          ))}
          {!said.year_held ? (
            <p className="text-pw-ink-500 px-6 py-4 text-[12.5px] leading-[19px] sm:px-8">
              No year-on-year comparison yet: PPCWay holds {said.held_days ?? 0} days of this
              account&rsquo;s history. It fills in as the days pass; nothing is estimated to cover
              the gap.
            </p>
          ) : null}
        </dl>
      </div>
    </PwCard>
  );
}

function Verdict({ figure }: { figure: Figure }) {
  if (!figure.verdict || figure.verdict === "none") return null;
  return (
    <span title={figure.test ? `Tested as ${figure.test}.` : undefined}>
      <Chip tone={VERDICT_TONES[figure.verdict] ?? "neutral"}>
        {VERDICT_WORDS[figure.verdict] ?? figure.verdict}
      </Chip>
    </span>
  );
}

/* ---------- the quieter figures ---------- */

function OtherFigures({ said }: { said: ReportSaid }) {
  const currency = said.currency ?? "";
  const days = said.days ?? 30;
  const f = figuresByKey(said);
  const rest = [f.lead_rate, f.clicks, f.click_rate].filter((x): x is Figure => Boolean(x));
  if (rest.length === 0) return null;
  return (
    <PwCard>
      <dl className="divide-pw-border grid grid-cols-1 divide-y sm:grid-cols-3 sm:divide-x sm:divide-y-0">
        {rest.map((figure) => (
          <div key={figure.key} className="flex flex-col gap-1 px-6 py-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <dt className="text-pw-ink-600 text-[14px] leading-[20px] font-medium">
                {figure.label}
              </dt>
              <Verdict figure={figure} />
            </div>
            <dd>
              <p className={cn(DISPLAY, "pw-num text-[26px] leading-[32px] font-semibold")}>
                {showFigure(figure.value, figure.kind, currency)}
              </p>
              <p className="text-pw-ink-500 mt-1 text-[13px] leading-[19px]">
                {figure.before !== null || figure.year_ago !== null
                  ? compared(figure, days, currency)
                  : figure.words}
              </p>
            </dd>
          </div>
        ))}
      </dl>
    </PwCard>
  );
}

/* ---------- day by day ---------- */

function DayByDay({
  bars,
  currency,
  said,
}: {
  bars: DayBar[];
  currency: string;
  said: ReportSaid;
}) {
  if (bars.length < 2) return null;
  const mostLeads = Math.max(...bars.map((b) => b.leads), 1);
  const mostCost = Math.max(...bars.map((b) => b.cost), 0.01);
  const spent = bars.reduce((n, b) => n + b.cost, 0);
  const leads = bars.reduce((n, b) => n + b.leads, 0);
  const columns = { gridTemplateColumns: `repeat(${bars.length}, minmax(0, 1fr))` };
  const gap = bars.length > 45 ? "gap-[1px]" : "gap-[3px]";
  // A date under the first bar of each week, counted back from the last day so
  // the last label is always the last day.
  const ticks = new Set(bars.map((_, i) => i).filter((i) => (bars.length - 1 - i) % 7 === 0));
  const firstTick = Math.min(...ticks);
  return (
    <PwCard className="p-6 sm:p-8">
      <h2 className="text-[17px] leading-[22px] font-semibold">Day by day</h2>
      <p className="text-pw-ink-700 mt-1.5 text-[15px] leading-[23px]">
        {busiestDay(said.series, currency)}
      </p>
      <figure
        className="mt-6"
        aria-label={`Leads and spend for each of ${bars.length} days: ${Math.round(leads)} leads for ${moneyOf(spent, currency)} in all.`}
      >
        <div className="grid grid-cols-[64px_minmax(0,1fr)] gap-x-3">
          <Axis label="Leads" top={String(Math.round(mostLeads))} />
          <div className={cn("grid h-[132px] items-end", gap)} style={columns}>
            {bars.map((b) => (
              <span
                key={b.date}
                title={`${weekdayDayMonth(b.date)}: ${Math.round(b.leads)} leads for ${moneyOf(b.cost, currency)}`}
                className={cn(
                  "block rounded-t-[3px]",
                  b.leads > 0 ? "bg-pw-blue" : "bg-pw-ink-200",
                )}
                style={{
                  height: b.leads > 0 ? `${Math.max(3, (b.leads / mostLeads) * 100)}%` : "2px",
                }}
              />
            ))}
          </div>

          <div className="col-span-2 h-4" />

          <Axis label="Spend" top={moneyOf(mostCost, currency)} />
          <div className={cn("grid h-[56px] items-end", gap)} style={columns}>
            {bars.map((b) => (
              <span
                key={b.date}
                title={`${weekdayDayMonth(b.date)}: ${moneyOf(b.cost, currency)}`}
                className="bg-pw-ink-200 block rounded-t-[2px]"
                style={{
                  height: b.cost > 0 ? `${Math.max(3, (b.cost / mostCost) * 100)}%` : "1px",
                }}
              />
            ))}
          </div>

          <span />
          <div className={cn("mt-2 grid", gap)} style={columns}>
            {bars.map((b, i) => (
              <span
                key={b.date}
                className="text-pw-ink-400 relative h-4 text-[11.5px] leading-4 whitespace-nowrap"
              >
                {ticks.has(i) ? (
                  <span
                    className={cn(
                      "absolute top-0",
                      i === bars.length - 1 ? "right-0" : "left-0",
                      // On a phone the middle dates crowd each other: first and last only.
                      i !== bars.length - 1 && i !== firstTick ? "hidden sm:inline" : "",
                    )}
                  >
                    {dayMonth(b.date)}
                  </span>
                ) : null}
              </span>
            ))}
          </div>
        </div>
        <figcaption className="text-pw-ink-500 mt-4 text-[12.5px] leading-[18px]">
          Each column is one day. A grey stub in the top row is a day with no lead. Hover a column
          for its figures.
        </figcaption>
      </figure>
    </PwCard>
  );
}

function Axis({ label, top }: { label: string; top: string }) {
  return (
    <div className="flex flex-col justify-between py-0.5 text-right">
      <span className="text-pw-ink-500 pw-num text-[11.5px] leading-4">{top}</span>
      <span className="text-pw-ink-600 text-[12.5px] leading-4 font-medium">{label}</span>
    </div>
  );
}

/* ---------- where the leads came from ---------- */

function WhereFrom({ rows, currency }: { rows: CampaignShare[]; currency: string }) {
  return (
    <PwCard className="overflow-hidden">
      <div className="p-6 pb-4 sm:px-8 sm:pt-8">
        <h2 className="text-[17px] leading-[22px] font-semibold">Where the leads came from</h2>
        <p className="text-pw-ink-700 mt-1.5 max-w-[70ch] text-[15px] leading-[23px]">
          {whereFrom(rows, currency)}
        </p>
      </div>
      {rows.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left">
            <thead>
              <tr className="border-pw-border text-pw-ink-500 border-y text-[12.5px]">
                <th className="px-6 py-2.5 font-medium sm:pl-8">Campaign</th>
                <th className="px-3 py-2.5 text-right font-medium">Spend</th>
                <th className="px-3 py-2.5 text-right font-medium">Leads</th>
                <th className="px-3 py-2.5 text-right font-medium">Cost per lead</th>
                <th className="w-[22%] px-6 py-2.5 font-medium sm:pr-8">
                  Share of spend, then of leads
                </th>
              </tr>
            </thead>
            <tbody className="divide-pw-divider divide-y">
              {rows.map((row) => (
                <tr key={row.campaign_id}>
                  <td className="max-w-[300px] px-6 py-3.5 sm:pl-8">
                    <span className="block truncate text-[15px] font-semibold">{row.name}</span>
                    {row.gone ? (
                      <span className="text-pw-ink-500 text-[12.5px]">Deleted in Google Ads</span>
                    ) : null}
                  </td>
                  <td className="pw-num px-3 py-3.5 text-right text-[15px]">
                    {moneyOf(row.cost, currency)}
                  </td>
                  <td className="pw-num px-3 py-3.5 text-right text-[15px] font-semibold">
                    {Math.round(row.leads).toLocaleString("en-GB")}
                  </td>
                  <td className="pw-num px-3 py-3.5 text-right text-[15px]">
                    {row.leads > 0 ? moneyOf(row.cost_per_lead, currency) : "No leads"}
                  </td>
                  <td className="px-6 py-3.5 sm:pr-8">
                    <ShareBar share={row.costShare} tone="spend" />
                    <ShareBar share={row.leadShare} tone="leads" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="h-4" />
      )}
    </PwCard>
  );
}

function ShareBar({ share, tone }: { share: number; tone: "spend" | "leads" }) {
  return (
    <span className="flex items-center gap-2.5 py-[3px]">
      <span className="relative h-[6px] flex-1">
        <span
          className={cn(
            "absolute inset-y-0 left-0 rounded-full",
            tone === "leads" ? "bg-pw-blue" : "bg-pw-ink-200",
          )}
          style={{ width: `${Math.max(share > 0 ? 2 : 0, share * 100)}%` }}
        />
      </span>
      <span
        className={cn(
          "pw-num w-[112px] shrink-0 text-[12.5px] leading-4",
          tone === "leads" ? "text-pw-ink font-semibold" : "text-pw-ink-500",
        )}
      >
        {sharePercent(share)} of {tone}
      </span>
    </span>
  );
}

/* ---------- what PPCWay changed ---------- */

function Changes({ said }: { said: ReportSaid }) {
  const changes = said.changes ?? [];
  return (
    <PwCard className="overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-4 p-6 pb-4 sm:px-8 sm:pt-8">
        <div className="min-w-0">
          <h2 className="text-[17px] leading-[22px] font-semibold">What PPCWay changed</h2>
          <p className="text-pw-ink-700 mt-1.5 max-w-[70ch] text-[15px] leading-[23px]">
            {changesSentence(said)}
          </p>
        </div>
        <Link
          href="/otto"
          className="text-pw-blue hover:text-pw-blue-hover flex items-center gap-1.5 pt-0.5 text-[14px] font-semibold"
        >
          Open Otto inbox
          <ArrowRight size={14} weight="bold" />
        </Link>
      </div>
      {changes.length > 0 ? (
        <ol className="border-pw-border divide-pw-divider divide-y border-t">
          {changes.map((change) => (
            <ChangeRow key={change.id} change={change} />
          ))}
        </ol>
      ) : (
        <div className="h-4" />
      )}
    </PwCard>
  );
}

function ChangeRow({ change }: { change: ReportChange }) {
  const status = CHANGE_STATUS[change.status] ?? { label: change.status, tone: "neutral" as const };
  return (
    <li className="grid grid-cols-[56px_minmax(0,1fr)] items-start gap-x-4 gap-y-2 px-6 py-4 sm:grid-cols-[64px_minmax(0,1fr)_auto] sm:px-8">
      <span className="pw-num text-pw-ink-500 pt-0.5 text-[13px] leading-[20px]">
        {changeDay(change)}
      </span>
      <span className="min-w-0">
        <span className="block text-[15px] leading-[21px] font-semibold">{change.title}</span>
        {change.target.label ? (
          <span className="text-pw-ink-600 block truncate text-[14px] leading-[20px]">
            {change.target.label}
          </span>
        ) : null}
        {change.words ? (
          <span className="text-pw-ink-500 mt-1 block text-[13px] leading-[19px]">
            {change.words}
          </span>
        ) : null}
      </span>
      <span className="col-start-2 sm:col-start-auto">
        <Chip tone={status.tone}>{status.label}</Chip>
      </span>
    </li>
  );
}

/* ---------- the words ---------- */

function Words({ said }: { said: ReportSaid }) {
  const definitions = said.definitions ?? [];
  if (definitions.length === 0) return null;
  return (
    <PwCard>
      <details className="group">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-4 p-6 sm:px-8 [&::-webkit-details-marker]:hidden">
          <span>
            <span className="block text-[17px] leading-[22px] font-semibold">
              What these words mean
            </span>
            <span className="text-pw-ink-500 mt-1 block text-[14px] leading-[20px]">
              How each figure is counted, and how a real change is told from ordinary wobble.
            </span>
          </span>
          <CaretDown
            size={18}
            weight="bold"
            className="text-pw-ink-500 shrink-0 transition-transform duration-200 group-open:rotate-180 motion-reduce:transition-none"
          />
        </summary>
        <dl className="border-pw-border grid gap-x-10 gap-y-5 border-t px-6 py-6 sm:grid-cols-2 sm:px-8">
          {definitions.map((d) => (
            <div key={d.term}>
              <dt className="text-[14px] leading-[20px] font-semibold">{d.term}</dt>
              <dd className="text-pw-ink-600 mt-1 text-[14px] leading-[21px]">{d.what}</dd>
            </div>
          ))}
        </dl>
      </details>
    </PwCard>
  );
}
