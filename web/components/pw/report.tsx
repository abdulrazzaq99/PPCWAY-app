import { money } from "@/components/pw/campaigns";
import { Chip, PwCard } from "@/components/pw/shell";
import type { AdsDay } from "@/lib/ads";
import { cn } from "@/lib/cn";
import type { Figure, ReportSaid } from "@/lib/reports";
import { ago } from "@/lib/when";

/*
  The report, as the app shows it and as a shared link shows it: one component,
  because the owner and the accountant they send it to should be reading the
  same page.

  Every figure carries a verdict rather than an arrow. Eleven leads last month
  and eight this month is not a thirty per cent collapse, and a report that
  prints the arrow without the arithmetic teaches somebody to panic on a Tuesday
  and spend money fixing nothing.
*/
const TONES: Record<string, "warn" | "good" | "neutral" | "info"> = {
  real: "warn",
  normal: "neutral",
  thin: "neutral",
  none: "neutral",
};

const VERDICTS: Record<string, string> = {
  real: "A real change",
  normal: "Within the normal range",
  thin: "Too little data to tell",
};

function show(figure: Figure, currency: string): string {
  if (figure.kind === "money") return figure.value ? money(figure.value, currency) : "—";
  if (figure.kind === "rate") return figure.value ? `${figure.value}%` : "—";
  return Math.round(figure.value).toLocaleString();
}

function showValue(value: number, kind: string, currency: string): string {
  if (kind === "money") return money(value, currency);
  if (kind === "rate") return `${value}%`;
  return Math.round(value).toLocaleString();
}

export function Report({ said, action }: { said: ReportSaid; action?: React.ReactNode }) {
  const currency = said.currency ?? "";
  const days = said.days ?? 30;
  const figures = said.figures ?? [];

  return (
    <>
      <PwCard className="p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 className="text-[17px] leading-[22px] font-semibold">In one sentence</h2>
            <p className="mt-2 max-w-[760px] text-[17px] leading-[27px]">{said.sentence}</p>
            <p className="text-pw-ink-400 mt-3 text-[13px]">
              {said.starts_on} to {said.ends_on}
              {said.looked_at ? ` · read from your account ${ago(said.looked_at)}` : ""}
            </p>
          </div>
          {action}
        </div>
      </PwCard>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {figures.map((figure) => (
          <PwCard key={figure.key} className="flex flex-col justify-between p-5">
            <div className="flex items-start justify-between gap-3">
              <span className="text-[14px] leading-[18px] font-semibold">{figure.label}</span>
              {figure.verdict !== "none" ? (
                <Chip tone={TONES[figure.verdict] ?? "neutral"}>
                  {VERDICTS[figure.verdict] ?? figure.verdict}
                </Chip>
              ) : null}
            </div>
            <p className="pw-num display mt-3 text-[30px] leading-[36px] font-semibold">
              {show(figure, currency)}
            </p>
            <p className="text-pw-ink-500 mt-1 text-[13px] leading-[19px]">
              {figure.before === null ? (
                `No earlier ${days} days to compare with.`
              ) : (
                <>
                  Was {showValue(figure.before, figure.kind, currency)}
                  {figure.change === null ? "" : `, ${Math.abs(figure.change)}% `}
                  {figure.change === null ? "" : figure.change > 0 ? "up" : "down"}
                </>
              )}
              {figure.year_ago !== null
                ? ` · ${showValue(figure.year_ago, figure.kind, currency)} a year ago`
                : ""}
            </p>
            <p className="text-pw-ink-700 mt-2 text-[13px] leading-[19px]">{figure.words}</p>
            {figure.test ? (
              <p className="text-pw-ink-400 mt-1 text-[12px]">Tested as {figure.test}.</p>
            ) : null}
          </PwCard>
        ))}
      </div>

      {!said.year_held ? (
        <p className="text-pw-ink-500 text-[14px] leading-[21px]">
          There is no year-on-year column yet: we hold {said.held_days ?? 0} days of this
          account&rsquo;s history. It fills in as the days pass, and nothing here is estimated to
          cover the gap.
        </p>
      ) : null}

      <Trend series={said.series} currency={currency} />

      <PwCard className="overflow-hidden">
        <h2 className="px-5 py-5 text-[17px] leading-[22px] font-semibold sm:px-6">By campaign</h2>
        {(said.campaigns?.length ?? 0) === 0 ? (
          <p className="text-pw-ink-500 px-5 pb-6 text-[15px] sm:px-6">
            No campaign spent anything in this period.
          </p>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="border-pw-divider text-pw-ink-400 border-y text-[12px]">
                <th className="px-5 py-2 font-semibold sm:px-6">Campaign</th>
                <th className="px-3 py-2 text-right font-semibold">Spend</th>
                <th className="px-3 py-2 text-right font-semibold">Leads</th>
                <th className="px-5 py-2 text-right font-semibold sm:px-6">Cost per lead</th>
              </tr>
            </thead>
            <tbody>
              {(said.campaigns ?? []).map((row) => (
                <tr key={row.campaign_id} className="border-pw-divider border-b last:border-0">
                  <td className="max-w-[260px] truncate px-5 py-3 text-[15px] font-semibold sm:px-6">
                    {row.name}
                    {row.gone ? (
                      <span className="text-pw-ink-400"> · no longer running</span>
                    ) : null}
                  </td>
                  <td className="pw-num px-3 py-3 text-right text-[15px]">
                    {money(row.cost, currency)}
                  </td>
                  <td className="pw-num px-3 py-3 text-right text-[15px]">
                    {Math.round(row.leads)}
                  </td>
                  <td className="pw-num px-5 py-3 text-right text-[15px] sm:px-6">
                    {row.cost_per_lead ? money(row.cost_per_lead, currency) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </PwCard>

      <PwCard className="p-5 sm:p-6">
        <h2 className="text-[17px] leading-[22px] font-semibold">What these words mean</h2>
        <ul className="divide-pw-divider mt-3 divide-y">
          {(said.definitions ?? []).map((d) => (
            <li key={d.term} className="flex flex-col gap-1 py-3 sm:flex-row sm:gap-4">
              <span className="text-[14px] font-semibold sm:w-[200px] sm:shrink-0">{d.term}</span>
              <span className="text-pw-ink-600 text-[14px] leading-[21px]">{d.what}</span>
            </li>
          ))}
        </ul>
      </PwCard>
    </>
  );
}

/* Spend by day, with a dot on each day that brought a lead. */
function Trend({ series, currency }: { series: AdsDay[] | undefined; currency: string }) {
  const days = series ?? [];
  if (days.length < 2) return null;
  const peak = Math.max(...days.map((d) => d.cost), 0.01);
  const spent = days.reduce((n, d) => n + d.cost, 0);
  const leads = days.reduce((n, d) => n + d.leads, 0);
  return (
    <PwCard className="p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-[17px] leading-[22px] font-semibold">Day by day</h2>
        <p className="text-pw-ink-400 text-[12px]">
          Bar height is the day&rsquo;s spend; a dot marks a day that brought a lead.
        </p>
      </div>
      <div
        role="img"
        aria-label={`Spend by day over ${days.length} days: ${money(spent, currency)} and ${Math.round(leads)} leads.`}
        className="mt-4 flex h-[160px] items-end gap-[2px]"
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
        <span>{money(spent, currency)} in all</span>
        <span>{days[days.length - 1]?.date}</span>
      </div>
    </PwCard>
  );
}
