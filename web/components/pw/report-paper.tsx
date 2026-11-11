import Image from "next/image";
import { cn } from "@/lib/cn";
import { moneyOf, roundMoney } from "@/lib/money";
import {
  CHANGE_STATUS,
  VERDICT_WORDS,
  absoluteUtc,
  accountNumber,
  busiestWeek,
  campaignShares,
  changeDay,
  changesSentence,
  compared,
  dayMonth,
  figuresByKey,
  paperParagraph,
  periodWords,
  sharePercent,
  showFigure,
  weekBars,
} from "@/lib/report-view";
import type { Figure, ReportSaid } from "@/lib/reports";

/*
  The report on paper, from the "V2 · Report · PDF" frames: an A4 sheet 794px
  wide with 60px margins, the wordmark and the dates, a rule, the business, one
  plain paragraph, three figures, a weekly chart and where the leads came from.
  Page 2 lists every change PPCWay made, then the quieter figures and what the
  words mean.

  It is the page the backend's Chromium prints, signed in as whoever asked, the
  moment the PDF is downloaded: so the PDF is always today's figures, and this
  is the only layout of it there is. Chromium adds the footer with the page
  numbers; everything else is here.
*/

const DISPLAY = "font-(family-name:--font-outfit) tracking-[-0.015em]";

/** Campaigns listed by name on page 1; the rest are summed in one line. */
const MOST_CAMPAIGNS = 4;

export function ReportPaper({ said }: { said: ReportSaid }) {
  const currency = said.currency ?? "";
  const days = said.days ?? 30;
  const period = periodWords(said.starts_on ?? "", said.ends_on ?? "");
  const f = figuresByKey(said);
  const rows = campaignShares(said.campaigns);
  const weeks = days <= 7 ? null : weekBars(said.series);
  const business = said.business || "Your Google Ads account";

  return (
    <article className="text-pw-ink mx-auto w-full max-w-[794px] bg-white [print-color-adjust:exact]">
      {/* ---------- page 1 ---------- */}
      <section className="px-[60px] pt-[18px] pb-[12px]">
        <header className="flex items-end justify-between gap-6">
          <Image
            src="/brand/ppcway-logo.svg"
            alt="PPCWay"
            width={122}
            height={28}
            priority
            className="h-[28px] w-auto"
          />
          <p className="text-pw-ink-500 text-right text-[11px] leading-[15px]">
            <span className="text-pw-ink-700 block font-semibold">Google Ads report</span>
            {period}
          </p>
        </header>
        <div className="bg-pw-ink mt-4 h-[1.5px]" />

        <h1 className={cn(DISPLAY, "mt-6 text-[34px] leading-[40px] font-semibold")}>{business}</h1>
        <p className="text-pw-ink-500 mt-1.5 text-[12px] leading-[17px]">
          {said.customer_id ? `Google Ads account ${accountNumber(said.customer_id)}, ` : ""}
          the last {days} days
        </p>

        <h2 className="text-pw-ink-500 mt-6 text-[12px] leading-[16px] font-semibold">
          In one paragraph
        </h2>
        <p className="mt-2 max-w-[600px] text-[16px] leading-[25px]">
          {paperParagraph(said, rows)}
        </p>

        <div className="mt-6 grid grid-cols-3 gap-3">
          {[f.leads, f.cost, f.cost_per_lead].map((figure, i) =>
            figure ? (
              <StatBox key={figure.key} figure={figure} first={i === 0} said={said} />
            ) : null,
          )}
        </div>

        {weeks && weeks.length > 1 ? (
          <Weeks weeks={weeks} currency={currency} />
        ) : (
          <DaysChart said={said} />
        )}

        <h2 className={cn(DISPLAY, "mt-7 text-[18px] leading-[24px] font-semibold")}>
          Where the leads came from
        </h2>
        {rows.length === 0 ? (
          <p className="text-pw-ink-600 mt-2 text-[13px] leading-[20px]">
            No campaign spent anything in this period.
          </p>
        ) : (
          <ul className="divide-pw-divider border-pw-border mt-3 divide-y border-t">
            {rows.slice(0, MOST_CAMPAIGNS).map((row) => (
              <li
                key={row.campaign_id}
                className="grid break-inside-avoid grid-cols-[minmax(0,1fr)_150px] items-center gap-6 py-2.5"
              >
                <span className="min-w-0">
                  <span className="block truncate text-[13.5px] leading-[19px] font-semibold">
                    {row.name}
                  </span>
                  <span className="text-pw-ink-500 pw-num block text-[11.5px] leading-[17px]">
                    {Math.round(row.leads).toLocaleString("en-GB")}{" "}
                    {Math.round(row.leads) === 1 ? "lead" : "leads"} for{" "}
                    {moneyOf(row.cost, currency)}
                    {row.leads > 0 ? `, ${moneyOf(row.cost_per_lead, currency)} a lead` : ""}
                    {row.gone ? ", deleted in Google Ads" : ""}
                  </span>
                </span>
                <span className="flex flex-col gap-1">
                  <span className="flex items-baseline justify-between gap-2">
                    <span className="text-pw-ink-500 text-[10.5px]">of the leads</span>
                    <span
                      className={cn(DISPLAY, "pw-num text-[17px] leading-[20px] font-semibold")}
                    >
                      {sharePercent(row.leadShare)}
                    </span>
                  </span>
                  <span className="relative block h-[5px]">
                    <span
                      className="bg-pw-blue absolute inset-y-0 left-0 rounded-full"
                      style={{
                        width: `${Math.max(row.leadShare > 0 ? 2 : 0, row.leadShare * 100)}%`,
                      }}
                    />
                  </span>
                </span>
              </li>
            ))}
            {rows.length > MOST_CAMPAIGNS ? (
              <li className="text-pw-ink-500 py-3 text-[11.5px] leading-[17px]">
                And {rows.length - MOST_CAMPAIGNS} smaller{" "}
                {rows.length - MOST_CAMPAIGNS === 1 ? "campaign" : "campaigns"}, with{" "}
                {Math.round(
                  rows.slice(MOST_CAMPAIGNS).reduce((n, r) => n + r.leads, 0),
                ).toLocaleString("en-GB")}{" "}
                leads between them.
              </li>
            ) : null}
          </ul>
        )}
      </section>

      {/* ---------- page 2 ---------- */}
      <section className="break-before-page px-[60px] pt-[22px] pb-[24px]">
        <div className="text-pw-ink-500 flex items-baseline justify-between gap-6 text-[11px] leading-[15px]">
          <span className="text-pw-ink-700 font-semibold">{business}</span>
          <span>{period}</span>
        </div>
        <div className="bg-pw-border mt-3 h-px" />

        {said.changes ? (
          <>
            <h2 className={cn(DISPLAY, "mt-7 text-[24px] leading-[30px] font-semibold")}>
              Every change PPCWay made
            </h2>
            <p className="text-pw-ink-600 mt-1.5 max-w-[600px] text-[13px] leading-[20px]">
              {changesSentence(said, "paper")}
            </p>
            {said.changes.length > 0 ? (
              <ol className="divide-pw-divider border-pw-border mt-4 divide-y border-t">
                {said.changes.map((change) => {
                  const status = CHANGE_STATUS[change.status] ?? {
                    label: change.status,
                    tone: "neutral" as const,
                  };
                  return (
                    <li
                      key={change.id}
                      className="grid break-inside-avoid grid-cols-[52px_minmax(0,1fr)_auto] items-start gap-4 py-3"
                    >
                      <span className="pw-num text-pw-ink-500 text-[11.5px] leading-[18px]">
                        {changeDay(change)}
                      </span>
                      <span className="min-w-0">
                        <span className="block text-[13px] leading-[18px] font-semibold">
                          {change.title}
                          {change.target.label ? (
                            <span className="text-pw-ink-600 font-normal">
                              : {change.target.label}
                            </span>
                          ) : null}
                        </span>
                        {change.words ? (
                          <span className="text-pw-ink-500 mt-0.5 block text-[11.5px] leading-[17px]">
                            {change.words}
                          </span>
                        ) : null}
                      </span>
                      <span
                        className={cn(
                          "rounded-full px-2.5 py-[3px] text-[10.5px] leading-[14px] font-semibold whitespace-nowrap",
                          {
                            good: "bg-pw-good-bg text-pw-good-ink",
                            neutral: "bg-pw-muted text-pw-ink-600",
                            warn: "bg-pw-warn-bg text-pw-warn-ink",
                            bad: "bg-pw-bad-bg text-pw-bad-ink",
                          }[status.tone],
                        )}
                      >
                        {status.label}
                      </span>
                    </li>
                  );
                })}
              </ol>
            ) : null}
          </>
        ) : null}

        <h2 className={cn(DISPLAY, "mt-9 text-[18px] leading-[24px] font-semibold")}>
          The other figures
        </h2>
        <div className="border-pw-border divide-pw-border mt-3 grid break-inside-avoid grid-cols-3 divide-x border-y">
          {[f.lead_rate, f.clicks, f.click_rate].map((figure) =>
            figure ? (
              <div key={figure.key} className="px-4 py-3 first:pl-0">
                <p className="text-pw-ink-500 text-[11px] leading-[15px] font-medium">
                  {figure.label}
                </p>
                <p
                  className={cn(DISPLAY, "pw-num mt-0.5 text-[20px] leading-[26px] font-semibold")}
                >
                  {showFigure(figure.value, figure.kind, currency)}
                </p>
                <p className="text-pw-ink-500 mt-0.5 text-[10.5px] leading-[15px]">
                  {figure.before !== null || figure.year_ago !== null
                    ? compared(figure, days, currency)
                    : figure.words}
                </p>
              </div>
            ) : null,
          )}
        </div>

        <h2 className={cn(DISPLAY, "mt-9 text-[18px] leading-[24px] font-semibold")}>
          What these words mean
        </h2>
        <dl className="mt-3 grid grid-cols-2 gap-x-8 gap-y-3.5">
          {(said.definitions ?? []).map((d) => (
            <div key={d.term} className="break-inside-avoid">
              <dt className="text-[11.5px] leading-[16px] font-semibold">{d.term}</dt>
              <dd className="text-pw-ink-600 mt-0.5 text-[10.5px] leading-[15.5px]">{d.what}</dd>
            </div>
          ))}
        </dl>

        <div className="bg-pw-border mt-8 h-px" />
        <p className="text-pw-ink-500 mt-3 max-w-[600px] break-inside-avoid text-[10.5px] leading-[16px]">
          Every figure comes from your Google Ads account
          {said.looked_at ? `, as read at ${absoluteUtc(said.looked_at)}` : ""}. Whole days only, up
          to the end of {said.ends_on ? dayMonth(said.ends_on) : "yesterday"}: today is left out
          until Google has finished counting it.
          {!said.year_held
            ? ` There is no year-on-year comparison yet, because PPCWay holds ${said.held_days ?? 0} days of this account's history.`
            : ""}
        </p>
      </section>
    </article>
  );
}

function StatBox({ figure, first, said }: { figure: Figure; first: boolean; said: ReportSaid }) {
  const currency = said.currency ?? "";
  const days = said.days ?? 30;
  const value = showFigure(figure.value, figure.kind, currency);
  return (
    <div
      className={cn(
        "flex break-inside-avoid flex-col rounded-[10px] px-4 py-3",
        first ? "bg-pw-blue-tint" : "bg-pw-ground",
      )}
    >
      <p
        className={cn(
          "text-[11.5px] leading-[16px] font-medium",
          first ? "text-pw-blue-ink" : "text-pw-ink-500",
        )}
      >
        {figure.label === "Spend" ? "Spent" : figure.label}
      </p>
      <p className={cn(DISPLAY, "pw-num mt-1 text-[26px] leading-[31px] font-semibold")}>{value}</p>
      <p className="text-pw-ink-500 mt-1 text-[10.5px] leading-[15px]">
        {compared(figure, days, currency)}
      </p>
      {figure.verdict && figure.verdict !== "none" ? (
        <p
          className={cn(
            "mt-1.5 text-[10.5px] leading-[15px] font-semibold",
            figure.verdict === "real" ? "text-pw-warn-ink" : "text-pw-ink-600",
          )}
        >
          {VERDICT_WORDS[figure.verdict] ?? figure.verdict}
        </p>
      ) : null}
    </div>
  );
}

function Weeks({ weeks, currency }: { weeks: ReturnType<typeof weekBars>; currency: string }) {
  const most = Math.max(...weeks.map((w) => w.leads), 1);
  const last = weeks.length - 1;
  // Weeks are counted back from the last day, so only the first can be short.
  const span =
    Math.round(
      (Date.parse(`${weeks[0].ends}T12:00:00Z`) - Date.parse(`${weeks[0].starts}T12:00:00Z`)) /
        86_400_000,
    ) + 1;
  const short = span < 7 ? span : 0;
  return (
    <div className="break-inside-avoid">
      <h2 className={cn(DISPLAY, "mt-7 text-[18px] leading-[24px] font-semibold")}>
        Leads each week
      </h2>
      <p className="text-pw-ink-600 mt-1 text-[13px] leading-[20px]">{busiestWeek(weeks)}</p>
      <div
        className="mt-4 grid items-end gap-3"
        style={{ gridTemplateColumns: `repeat(${weeks.length}, minmax(0, 1fr))` }}
      >
        {weeks.map((w, i) => (
          <div key={w.starts} className="flex h-[118px] flex-col justify-end">
            <span className="pw-num text-pw-ink-700 mb-1 text-center text-[11px] leading-[14px] font-semibold">
              {Math.round(w.leads).toLocaleString("en-GB")}
            </span>
            <span
              className={cn(
                "block rounded-t-[4px]",
                i === last ? "bg-pw-blue" : "bg-pw-blue-light",
              )}
              style={{ height: `${Math.max(2, (w.leads / most) * 90)}px` }}
            />
          </div>
        ))}
      </div>
      <div className="bg-pw-ink-300 h-px" />
      <div
        className="mt-1.5 grid gap-3"
        style={{ gridTemplateColumns: `repeat(${weeks.length}, minmax(0, 1fr))` }}
      >
        {weeks.map((w) => (
          <span key={w.starts} className="text-center">
            <span className="text-pw-ink-500 block text-[10px] leading-[14px] font-medium">
              {dayMonth(w.starts)}
            </span>
            <span className="text-pw-ink-400 pw-num block text-[9.5px] leading-[13px]">
              {roundMoney(w.cost, currency)}
            </span>
          </span>
        ))}
      </div>
      <p className="text-pw-ink-500 mt-2 text-[10.5px] leading-[15px]">
        Each bar is a week, named by its first day, with what it cost underneath.
        {short
          ? ` The first bar covers ${short} ${short === 1 ? "day" : "days"}, so it is shorter.`
          : ""}
      </p>
    </div>
  );
}

/* A seven-day report has one week, so it shows its days instead. */
function DaysChart({ said }: { said: ReportSaid }) {
  const series = said.series ?? [];
  if (series.length < 2) return null;
  const currency = said.currency ?? "";
  const most = Math.max(...series.map((d) => d.leads), 1);
  return (
    <div className="break-inside-avoid">
      <h2 className={cn(DISPLAY, "mt-7 text-[18px] leading-[24px] font-semibold")}>
        Leads each day
      </h2>
      <div
        className="mt-4 grid items-end gap-3"
        style={{ gridTemplateColumns: `repeat(${series.length}, minmax(0, 1fr))` }}
      >
        {series.map((d, i) => (
          <div key={d.date} className="flex h-[118px] flex-col justify-end">
            <span className="pw-num text-pw-ink-700 mb-1 text-center text-[11px] leading-[14px] font-semibold">
              {Math.round(d.leads)}
            </span>
            <span
              className={cn(
                "block rounded-t-[4px]",
                i === series.length - 1 ? "bg-pw-blue" : "bg-pw-blue-light",
              )}
              style={{ height: `${Math.max(2, (d.leads / most) * 90)}px` }}
            />
          </div>
        ))}
      </div>
      <div className="bg-pw-ink-300 h-px" />
      <div
        className="mt-1.5 grid gap-3"
        style={{ gridTemplateColumns: `repeat(${series.length}, minmax(0, 1fr))` }}
      >
        {series.map((d) => (
          <span key={d.date} className="text-center">
            <span className="text-pw-ink-500 block text-[10px] leading-[14px] font-medium">
              {dayMonth(d.date)}
            </span>
            <span className="text-pw-ink-400 pw-num block text-[9.5px] leading-[13px]">
              {moneyOf(d.cost, currency)}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
