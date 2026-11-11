import type { AdsDay, AdsRow } from "@/lib/ads";
import { moneyOf } from "@/lib/money";
import type { Figure, ReportChange, ReportSaid } from "@/lib/reports";
import { ago } from "@/lib/when";

/*
  What the report says, worked out once for the screen and the printed copy, so
  the page somebody reads and the PDF they forward cannot drift apart.

  Plain words come first: a sentence before a number, a number before a chart.
*/

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function parts(iso: string): { y: number; m: number; d: number; w: number } {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  // Noon UTC, so no time zone can push the day over midnight.
  const w = new Date(Date.UTC(y, m - 1, d, 12)).getUTCDay();
  return { y, m, d, w };
}

/** "10 Nov". */
export function dayMonth(iso: string): string {
  const { m, d } = parts(iso);
  return `${d} ${MONTHS[m - 1]}`;
}

/** "Tue 4 Nov". */
export function weekdayDayMonth(iso: string): string {
  const { w } = parts(iso);
  return `${WEEKDAYS[w]} ${dayMonth(iso)}`;
}

/** "12 Oct to 10 Nov 2026", with the first year only when the years differ. */
export function periodWords(starts: string, ends: string): string {
  if (!starts || !ends) return "";
  const a = parts(starts);
  const b = parts(ends);
  return `${dayMonth(starts)}${a.y === b.y ? "" : ` ${a.y}`} to ${dayMonth(ends)} ${b.y}`;
}

/** "258-058-6343", the way Google Ads writes an account number. */
export function accountNumber(id: string | undefined): string {
  const digits = (id ?? "").replace(/\D/g, "");
  return digits.length === 10
    ? `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6)}`
    : digits;
}

/**
 * A backend time, always UTC. A database that drops the zone sends a bare
 * "2026-11-11T09:58:08", which a browser would read as its own local time.
 */
export function asUtc(iso: string): string {
  return /(?:Z|[+-]\d{2}:?\d{2})$/.test(iso) ? iso : `${iso}Z`;
}

/** One figure written for people, with "None" rather than a bare dash. */
export function showFigure(value: number, kind: string, currency: string): string {
  if (kind === "money") return value ? moneyOf(value, currency) : "None";
  if (kind === "rate") return `${value.toLocaleString("en-GB", { maximumFractionDigits: 1 })}%`;
  return Math.round(value).toLocaleString("en-GB");
}

/** "Was 288 in the 30 days before, and 241 a year ago." */
export function compared(figure: Figure, days: number, currency: string): string {
  const parts: string[] = [];
  if (figure.before !== null) {
    const move =
      figure.change === null || figure.change === 0
        ? ""
        : ` (${figure.change > 0 ? "up" : "down"} ${Math.abs(figure.change).toLocaleString(
            "en-GB",
            {
              maximumFractionDigits: Math.abs(figure.change) >= 10 ? 0 : 1,
            },
          )}%)`;
    parts.push(
      `Was ${showFigure(figure.before, figure.kind, currency)} in the ${days} days before${move}`,
    );
  } else {
    parts.push(`No earlier ${days} days to compare with`);
  }
  if (figure.year_ago !== null) {
    parts.push(`${showFigure(figure.year_ago, figure.kind, currency)} a year ago`);
  }
  return `${parts.join(", and ")}.`;
}

export const VERDICT_WORDS: Record<string, string> = {
  real: "A real change",
  normal: "Within the normal range",
  thin: "Too little data to tell",
};

export const VERDICT_TONES: Record<string, "warn" | "neutral"> = {
  real: "warn",
  normal: "neutral",
  thin: "neutral",
};

/** The figures by key, so a layout can place each one where it belongs. */
export function figuresByKey(said: ReportSaid): Record<string, Figure | undefined> {
  return Object.fromEntries((said.figures ?? []).map((f) => [f.key, f]));
}

/*
  How current the figures are, said plainly. The report covers whole days and
  stops at yesterday: today is still being counted by Google, and a half-day
  beside thirty whole ones would read as a collapse every morning.
*/
export function freshness(said: ReportSaid): string {
  const through = said.ends_on ? `up to the end of ${dayMonth(said.ends_on)}` : "";
  const read = said.looked_at ? ` Read from Google Ads ${ago(asUtc(said.looked_at))}.` : "";
  return `Whole days only, ${through}. Today is left out until Google has finished counting it.${read}`;
}

/* ---------- day by day ---------- */

export type DayBar = { date: string; leads: number; cost: number };

export function dayBars(series: AdsDay[] | undefined): DayBar[] {
  return (series ?? []).map((d) => ({ date: d.date, leads: d.leads, cost: d.cost }));
}

/** "Your busiest day was Tue 4 Nov, with 23 leads for $4.12." */
export function busiestDay(series: AdsDay[] | undefined, currency: string): string {
  const days = series ?? [];
  if (days.length === 0) return "No days to show yet.";
  const best = [...days].sort((a, b) => b.leads - a.leads || a.cost - b.cost)[0];
  if (!best || best.leads <= 0) return "No day in this period brought a lead.";
  const n = Math.round(best.leads);
  return `Your busiest day was ${weekdayDayMonth(best.date)}, with ${n} ${n === 1 ? "lead" : "leads"} for ${moneyOf(best.cost, currency)}.`;
}

export type WeekBar = { starts: string; ends: string; leads: number; cost: number };

/**
 * Seven-day buckets counted back from the last day, so the last bar is always a
 * whole week and a short first bucket is the one that admits it.
 */
export function weekBars(series: AdsDay[] | undefined): WeekBar[] {
  const days = series ?? [];
  const weeks: WeekBar[] = [];
  for (let end = days.length; end > 0; end -= 7) {
    const slice = days.slice(Math.max(0, end - 7), end);
    weeks.unshift({
      starts: slice[0].date,
      ends: slice[slice.length - 1].date,
      leads: slice.reduce((n, d) => n + d.leads, 0),
      cost: slice.reduce((n, d) => n + d.cost, 0),
    });
  }
  return weeks;
}

/* ---------- where the leads came from ---------- */

export type CampaignShare = AdsRow & { leadShare: number; costShare: number };

export function campaignShares(rows: AdsRow[] | undefined): CampaignShare[] {
  const list = (rows ?? []).filter((r) => r.cost > 0 || r.leads > 0);
  const cost = list.reduce((n, r) => n + r.cost, 0);
  const leads = list.reduce((n, r) => n + r.leads, 0);
  return list
    .map((r) => ({
      ...r,
      costShare: cost ? r.cost / cost : 0,
      leadShare: leads ? r.leads / leads : 0,
    }))
    .sort((a, b) => b.leads - a.leads || b.cost - a.cost);
}

function percent(share: number): string {
  const p = share * 100;
  return p > 0 && p < 1 ? "under 1%" : `${Math.round(p)}%`;
}

export { percent as sharePercent };

/** "PDFezy | Search brought 284 of your 312 leads, 91% of them, for 80% of the spend." */
export function whereFrom(rows: CampaignShare[], currency: string): string {
  if (rows.length === 0) return "No campaign spent anything in this period.";
  const total = Math.round(rows.reduce((n, r) => n + r.leads, 0));
  const top = rows[0];
  if (total === 0) {
    const spent = rows.reduce((n, r) => n + r.cost, 0);
    return `Your campaigns spent ${moneyOf(spent, currency)} and none of them brought a lead.`;
  }
  if (rows.length === 1) {
    return `${top.name} brought all ${total} ${total === 1 ? "lead" : "leads"}.`;
  }
  return `${top.name} brought ${Math.round(top.leads)} of your ${total} leads, ${percent(top.leadShare)} of them, for ${percent(top.costShare)} of the spend.`;
}

/* ---------- what PPCWay changed ---------- */

export const CHANGE_STATUS: Record<
  string,
  { label: string; tone: "good" | "neutral" | "warn" | "bad" }
> = {
  applied: { label: "Made", tone: "good" },
  approved: { label: "Waiting to be made", tone: "neutral" },
  reverted: { label: "Undone", tone: "warn" },
  failed: { label: "Did not go through", tone: "bad" },
  rejected: { label: "Stopped by a safety check", tone: "neutral" },
};

/** The day a change belongs to: made, or failing that approved. */
export function changeDay(change: ReportChange): string {
  const when = change.applied_at ?? change.approved_at ?? "";
  return when ? dayMonth(when) : "";
}

export function changesSentence(said: ReportSaid, on: "screen" | "paper" = "screen"): string {
  const shown = said.changes?.length ?? 0;
  const all = said.changes_in_all ?? shown;
  const days = said.days ?? 30;
  if (all === 0) {
    return on === "paper"
      ? `PPCWay changed nothing in these ${days} days. Every suggestion waits for your approval, and none was approved in these dates.`
      : `PPCWay changed nothing in these ${days} days. Otto's suggestions wait in your inbox until you approve one.`;
  }
  const more = all > shown ? ` The ${shown} newest are listed here.` : "";
  return `${all} ${all === 1 ? "change" : "changes"} in these ${days} days. Each was approved before it was made, written down first, and can be undone for 30 days.${more}`;
}

/** "09:42 UTC on 11 Nov 2026": a printed copy is read days later, so never "minutes ago". */
export function absoluteUtc(iso: string | null | undefined): string {
  if (!iso) return "";
  const at = new Date(asUtc(iso));
  if (Number.isNaN(at.getTime())) return "";
  const hh = String(at.getUTCHours()).padStart(2, "0");
  const mm = String(at.getUTCMinutes()).padStart(2, "0");
  return `${hh}:${mm} UTC on ${at.getUTCDate()} ${MONTHS[at.getUTCMonth()]} ${at.getUTCFullYear()}`;
}

/** What follows the period's sentence: where the leads came from, and what PPCWay changed. */
export function afterTheSentence(
  said: ReportSaid,
  rows: CampaignShare[],
  on: "screen" | "paper" = "screen",
): string {
  const currency = said.currency ?? "";
  const lines: string[] = [];
  if (rows.length > 1 && rows.some((r) => r.leads > 0)) lines.push(whereFrom(rows, currency));
  if (said.changes) {
    const all = said.changes_in_all ?? said.changes.length;
    const where = on === "paper" ? "listed on page 2" : "listed below";
    lines.push(
      all === 0
        ? "PPCWay changed nothing in these dates."
        : `PPCWay made ${all} ${all === 1 ? "change" : "changes"}, ${where}.`,
    );
  }
  return lines.join(" ");
}

/** The printed copy's opening paragraph. */
export function paperParagraph(said: ReportSaid, rows: CampaignShare[]): string {
  return [said.sentence ?? "", afterTheSentence(said, rows, "paper")].filter(Boolean).join(" ");
}

/** "The busiest week was 3 to 9 Nov, with 85 leads." */
export function busiestWeek(weeks: WeekBar[]): string {
  const best = [...weeks].sort((a, b) => b.leads - a.leads)[0];
  if (!best || best.leads <= 0) return "No week in this period brought a lead.";
  const n = Math.round(best.leads);
  return `The busiest week was ${dayMonth(best.starts)} to ${dayMonth(best.ends)}, with ${n} ${n === 1 ? "lead" : "leads"}.`;
}
