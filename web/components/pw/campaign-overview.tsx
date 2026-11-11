import type { AdsDay, AdsNeed, AdsRow, AdsSummary } from "@/lib/ads";
import { cn } from "@/lib/cn";
import { moneyOf } from "@/lib/money";
import { learning } from "@/lib/when";

/*
  The top of the Campaigns screen, answering its one question before the
  table: which campaigns are earning their money?

  - The finding, in a sentence, computed from the rows: which campaign brings
    leads cheapest and by how much, or which one spends and brings none.
  - Four figures in one divided strip, each against the period before, with
    colour saying good or bad rather than up or down: cheaper leads are good.
  - "Money in, leads out", the element only an ads product has: each
    campaign's share of the spend directly above its share of the leads, so a
    campaign that takes most of the money for a few of the leads is seen at a
    glance, and one that does the reverse is too.
  - Leads a day across the window, with the busiest day named.

  Light, in the portal's own palette, with the brand blue on the data and
  nowhere else.
*/

/* One hue: the brand blue in steps, then neutrals, one per campaign. */
// Dates and amounts are formatted in one fixed locale, not the visitor's: the
// server renders this first and the browser renders it again, and two locales
// ("5 Nov" against "Nov 5") make React throw the server's page away.
const RAMP = ["#2f5bea", "#7d97f0", "#b9c6f2", "#dde4fb", "#c7ccd4", "#e4e7ec"];
const INK_ON = ["#ffffff", "#ffffff", "#1e3a8a", "#1e3a8a", "#374151", "#374151"];

export { moneyOf };

function shortName(name: string, most = 34): string {
  return name.length > most ? `${name.slice(0, most - 1).trimEnd()}…` : name;
}

/* ---------- the finding ---------- */

export function findingOf(summary: AdsSummary): string {
  const currency = summary.currency ?? "";
  const rows = (summary.campaigns ?? []).filter((r) => !r.gone);
  const paying = rows
    .filter((r) => r.leads > 0 && r.cost > 0)
    .sort((a, b) => a.cost_per_lead - b.cost_per_lead);
  if (paying.length >= 2) {
    const best = paying[0];
    const worst = paying[paying.length - 1];
    const ratio = worst.cost_per_lead / best.cost_per_lead;
    if (ratio >= 1.5) {
      const early = learning(best.starts_at)
        ? " It is in its first week, so give it a few more days."
        : "";
      return `${shortName(best.name)} brings leads at ${moneyOf(best.cost_per_lead, currency)} each, ${
        ratio >= 10 ? Math.round(ratio) : ratio.toFixed(1)
      }× cheaper than ${shortName(worst.name)} at ${moneyOf(worst.cost_per_lead, currency)}.${early}`;
    }
  }
  const wasting = rows.filter((r) => r.cost > 0 && r.leads <= 0).sort((a, b) => b.cost - a.cost)[0];
  if (wasting) {
    return `${shortName(wasting.name)} spent ${moneyOf(wasting.cost, currency)} and brought no leads.`;
  }
  if ((summary.cost ?? 0) > 0) {
    return `${Math.round(summary.leads ?? 0)} leads for ${moneyOf(summary.cost ?? 0, currency)} in the last ${
      summary.days ?? 30
    } days.`;
  }
  return "Nothing has been spent in this window yet.";
}

/* ---------- the four figures ---------- */

type Better = "up" | "down" | "neither";

function change(now: number, was: number | undefined, better: Better, days: number) {
  if (was === undefined || was === null) return { words: "", tone: "grey" as const };
  if (was === 0) {
    return now > 0
      ? { words: `+${Math.round(now)} (new)`, tone: "grey" as const }
      : { words: "", tone: "grey" as const };
  }
  const pct = ((now - was) / was) * 100;
  if (Math.abs(pct) < 0.5)
    return { words: `No change vs prior ${days} days`, tone: "grey" as const };
  const sign = pct > 0 ? "+" : "−";
  const good = better === "neither" ? null : (better === "up") === pct > 0;
  return {
    words: `${sign}${Math.abs(pct) >= 10 ? Math.round(Math.abs(pct)) : Math.abs(pct).toFixed(1)}% vs prior ${days} days`,
    tone: good === null ? ("grey" as const) : good ? ("good" as const) : ("bad" as const),
  };
}

function Figure({
  label,
  value,
  sub,
  tone = "grey",
}: {
  label: string;
  value: string;
  sub: string;
  tone?: "grey" | "good" | "bad";
}) {
  return (
    <div className="min-w-0 px-5 py-4 sm:px-6">
      <p className="text-pw-ink-500 text-[14px] leading-[18px]">{label}</p>
      <p className="pw-num mt-1 text-[26px] leading-[32px] font-semibold">{value}</p>
      <p
        className={cn(
          "mt-1 min-h-[18px] text-[13px] leading-[18px]",
          tone === "good"
            ? "text-pw-good-ink"
            : tone === "bad"
              ? "text-red-700"
              : "text-pw-ink-500",
        )}
      >
        {sub}
      </p>
    </div>
  );
}

export function Figures({ summary }: { summary: AdsSummary }) {
  const currency = summary.currency ?? "";
  const days = summary.days ?? 30;
  const spend = change(summary.cost ?? 0, summary.cost_before, "neither", days);
  const leads = change(summary.leads ?? 0, summary.leads_before, "up", days);
  const cpl = summary.cost_per_lead
    ? change(summary.cost_per_lead, summary.cost_per_lead_before || undefined, "down", days)
    : { words: "", tone: "grey" as const };

  const monthDay = summary.month_day ?? 0;
  const monthDays = summary.month_days ?? 0;
  const pace = monthDay > 0 ? ((summary.month_cost ?? 0) / monthDay) * monthDays : 0;
  const month = summary.monthly_budget
    ? `On pace for ${moneyOf(pace, currency)} of ${moneyOf(summary.monthly_budget, currency)}`
    : monthDay
      ? `On pace for ${moneyOf(pace, currency)} this month`
      : "";

  return (
    <div className="border-pw-border bg-pw-card divide-pw-divider grid grid-cols-2 divide-x divide-y overflow-hidden rounded-[18px] border lg:grid-cols-4 lg:divide-y-0">
      <Figure
        label="Spend"
        value={moneyOf(summary.cost ?? 0, currency)}
        sub={spend.words}
        tone={spend.tone}
      />
      <Figure
        label="Leads"
        value={String(Math.round(summary.leads ?? 0))}
        sub={leads.words}
        tone={leads.tone}
      />
      <Figure
        label="Cost per lead"
        value={summary.cost_per_lead ? moneyOf(summary.cost_per_lead, currency) : "—"}
        sub={cpl.words}
        tone={cpl.tone}
      />
      <Figure
        label={monthDay ? `This month, day ${monthDay} of ${monthDays}` : "This month"}
        value={moneyOf(summary.month_cost ?? 0, currency)}
        sub={month}
      />
    </div>
  );
}

/* ---------- money in, leads out ---------- */

type Slice = { key: string; name: string; share: number; colour: number };

function slices(rows: AdsRow[], by: "cost" | "leads"): Slice[] {
  const total = rows.reduce((sum, r) => sum + Math.max(0, r[by]), 0);
  if (total <= 0) return [];
  return rows.map((r, at) => ({
    key: r.campaign_id,
    name: r.name,
    share: Math.max(0, r[by]) / total,
    colour: Math.min(at, RAMP.length - 1),
  }));
}

function Strip({ label, parts }: { label: string; parts: Slice[] }) {
  return (
    <div className="grid grid-cols-[52px_minmax(0,1fr)] items-center gap-3">
      <span className="text-pw-ink-500 text-[13px] leading-[17px]">{label}</span>
      {parts.length ? (
        <div className="flex h-[34px] gap-[2px] overflow-hidden rounded-[8px]">
          {parts
            .filter((p) => p.share > 0)
            .map((p) => (
              <div
                key={p.key}
                title={`${p.name}: ${Math.round(p.share * 100)}% of ${label.toLowerCase()}`}
                className="flex min-w-[3px] items-center overflow-hidden px-2 text-[12px] leading-[16px] font-semibold whitespace-nowrap"
                style={{
                  width: `${p.share * 100}%`,
                  backgroundColor: RAMP[p.colour],
                  color: INK_ON[p.colour],
                }}
              >
                {p.share >= 0.14 ? `${Math.round(p.share * 100)}%` : ""}
              </div>
            ))}
        </div>
      ) : (
        <div className="bg-pw-muted text-pw-ink-500 flex h-[34px] items-center rounded-[8px] px-3 text-[12px]">
          None in this window
        </div>
      )}
    </div>
  );
}

export function MoneyAndLeads({ summary }: { summary: AdsSummary }) {
  const currency = summary.currency ?? "";
  // Biggest spender first, so the ramp's darkest step is the most money.
  const rows = [...(summary.campaigns ?? [])]
    .filter((r) => r.cost > 0 || r.leads > 0)
    .sort((a, b) => b.cost - a.cost);
  const top = rows.slice(0, RAMP.length - 1);
  const rest = rows.slice(RAMP.length - 1);
  const shown: AdsRow[] = rest.length
    ? [
        ...top,
        {
          campaign_id: "rest",
          name: `${rest.length} more`,
          status: "",
          budget: 0,
          cost: rest.reduce((s, r) => s + r.cost, 0),
          leads: rest.reduce((s, r) => s + r.leads, 0),
          cost_per_lead: 0,
        },
      ]
    : top;
  const spend = slices(shown, "cost");
  const leads = slices(shown, "leads");

  return (
    <section className="border-pw-border bg-pw-card rounded-[18px] border p-5 sm:p-6">
      <h2 className="text-[17px] leading-[22px] font-semibold">Money in, leads out</h2>
      <p className="text-pw-ink-500 mt-1 text-[14px] leading-[20px]">
        Each campaign&rsquo;s share of what you spent, above its share of the leads it brought.
      </p>
      <div className="mt-5 flex flex-col gap-2">
        <Strip label="Spend" parts={spend} />
        <Strip label="Leads" parts={leads} />
      </div>
      <table className="mt-5 w-full text-[14px] leading-[18px]">
        <thead>
          <tr className="text-pw-ink-500 text-[12px]">
            <th className="pb-2 text-left font-normal">Campaign</th>
            <th className="pb-2 text-right font-normal">Of spend</th>
            <th className="pb-2 text-right font-normal">Of leads</th>
            <th className="pb-2 text-right font-normal">A lead costs</th>
          </tr>
        </thead>
        <tbody>
          {shown.map((row, at) => {
            const ofSpend = spend[at]?.share ?? 0;
            const ofLeads = leads[at]?.share ?? 0;
            return (
              <tr key={row.campaign_id} className="border-pw-divider border-t">
                <td className="max-w-0 py-2 pr-3">
                  <span className="flex min-w-0 items-center gap-2">
                    <span
                      aria-hidden
                      className="size-[10px] shrink-0 rounded-[3px]"
                      style={{ backgroundColor: RAMP[Math.min(at, RAMP.length - 1)] }}
                    />
                    <span className="truncate" title={row.name}>
                      {row.name}
                    </span>
                  </span>
                </td>
                <td className="pw-num py-2 text-right">{Math.round(ofSpend * 100)}%</td>
                <td
                  className={cn(
                    "pw-num py-2 text-right",
                    ofLeads > ofSpend + 0.15 && "text-pw-good-ink font-semibold",
                    ofSpend > ofLeads + 0.25 && "font-semibold text-red-700",
                  )}
                >
                  {Math.round(ofLeads * 100)}%
                </td>
                <td className="pw-num py-2 text-right">
                  {row.leads > 0 ? moneyOf(row.cost / row.leads, currency) : "No leads"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

/* ---------- leads a day ---------- */

function dayName(iso: string): string {
  const d = new Date(`${iso}T12:00:00`);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

export function LeadsByDay({ series }: { series: AdsDay[] }) {
  const days = series ?? [];
  const most = Math.max(0, ...days.map((d) => d.leads));
  const top = Math.max(1, Math.ceil(most / 5) * 5 || 1);
  const busiest = days.reduce<AdsDay | null>(
    (b, d) => (b === null || d.leads > b.leads ? d : b),
    null,
  );
  const W = 100;
  const gap = days.length > 60 ? 0.15 : 0.6;
  const bar = days.length ? W / days.length - gap : 0;

  return (
    <section className="border-pw-border bg-pw-card flex flex-col rounded-[18px] border p-5 sm:p-6">
      <h2 className="text-[17px] leading-[22px] font-semibold">Leads a day</h2>
      <p className="text-pw-ink-500 mt-1 text-[14px] leading-[20px]">
        {busiest && busiest.leads > 0
          ? `Busiest: ${dayName(busiest.date)}, with ${Math.round(busiest.leads)} lead${Math.round(busiest.leads) === 1 ? "" : "s"}.`
          : "No leads counted in this window yet."}
      </p>
      <div className="relative mt-4 min-h-[170px] flex-1">
        {[0, 0.5, 1].map((f) => (
          <div
            key={f}
            className="border-pw-divider absolute right-0 left-7 border-t border-dashed"
            style={{ bottom: `${f * 100}%` }}
          >
            <span className="text-pw-ink-500 absolute -top-[8px] -left-7 w-6 text-right text-[11px] leading-[14px]">
              {Math.round(top * f)}
            </span>
          </div>
        ))}
        <svg
          viewBox={`0 0 ${W} 100`}
          preserveAspectRatio="none"
          className="absolute inset-y-0 right-0 left-7 h-full w-[calc(100%-1.75rem)]"
          role="img"
          aria-label={`Leads a day over ${days.length} days`}
        >
          {days.map((d, n) => {
            const h = (d.leads / top) * 100;
            return (
              <rect
                key={d.date}
                x={n * (bar + gap) + gap / 2}
                y={100 - h}
                width={Math.max(bar, 0.1)}
                height={Math.max(h, d.leads > 0 ? 1.5 : 0)}
                rx={0.6}
                fill="#2f5bea"
              >
                <title>{`${dayName(d.date)}: ${Math.round(d.leads)} leads, ${d.cost.toFixed(2)} spent`}</title>
              </rect>
            );
          })}
        </svg>
      </div>
      {days.length ? (
        <div className="text-pw-ink-500 mt-2 ml-7 flex justify-between text-[11px] leading-[14px]">
          <span>{dayName(days[0].date)}</span>
          <span>{dayName(days[Math.floor(days.length / 2)].date)}</span>
          <span>{dayName(days[days.length - 1].date)}</span>
        </div>
      ) : null}
    </section>
  );
}

/* ---------- what Google counted that is not a lead ---------- */

/*
  Said whenever Google counted conversions that PPCWay does not call leads, so
  a merchant comparing this screen with Google Ads is not left wondering why
  the numbers differ.
*/
export function SetAside({ summary }: { summary: AdsSummary }) {
  const set = Math.round(summary.not_leads ?? 0);
  if (set <= 0) return null;
  return (
    <p className="text-pw-ink-700 max-w-[820px] text-[14px] leading-[21px]">
      Google Ads also counted {set} page {set === 1 ? "view" : "views"} and similar as conversions.
      PPCWay doesn&rsquo;t count those as leads, so they&rsquo;re left out of the figures above.
      Calls, forms, sign-ups and sales still count.
    </p>
  );
}

/* ---------- what needs the merchant ---------- */

export function NeedsLine({ needs }: { needs: AdsNeed[] | undefined }) {
  const list = needs ?? [];
  if (!list.length) return null;
  return (
    <div className="border-pw-warn-border bg-pw-warn-bg text-pw-warn-ink rounded-[14px] border px-4 py-3 text-[14px] leading-[20px]">
      <span className="font-semibold">
        {list.length === 1 ? "One thing needs you:" : `${list.length} things need you:`}
      </span>{" "}
      {list
        .slice(0, 2)
        .map((n) => n.what)
        .join(" ")}
      {list.length > 2 ? ` And ${list.length - 2} more on your home screen.` : ""}
    </div>
  );
}
