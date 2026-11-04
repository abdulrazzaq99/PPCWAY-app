import Link from "next/link";
import {
  FATES,
  clock,
  count,
  dayOf,
  fateOf,
  type Fate,
  type JobRun,
  type Series,
} from "@/lib/admin";

/*
  The console's charts, drawn as HTML rather than a fixed SVG so the axis
  text stays 12px at every width (a scaled viewBox shrinks it to 6px on a
  phone) and nothing needs a script to appear.

  The rules are the tasteskill app chapter's: round ticks whose top sits above
  the largest value, 3-5 faint horizontal gridlines, no y-axis line, square
  columns, one hue on the main data and neutrals for the rest, x labels on one
  step that lands on today.
*/

/*
  Round ticks for a count: steps of 1, 2 or 5 x 10^n, five intervals at most,
  the top above the max. Five rather than four, because a top tick far above
  the tallest column leaves a band of empty plot that reads as a hole.
*/
export function ticks(max: number): number[] {
  const top = Math.max(max, 4);
  const raw = top / 5;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 5, 10].map((m) => Math.max(1, m * mag)).find((s) => s >= raw) ?? 10 * mag;
  let hi = Math.ceil(top / step) * step;
  if (hi <= max) hi += step;
  const out: number[] = [];
  for (let v = 0; v <= hi; v += step) out.push(v);
  return out;
}

/* Each fate's mark. The swatch in a legend is this same mark, scaled down. */
/*
  Applied is the main data and the only solid accent. Still open is the same
  hue as an outline: not done yet, and not louder than what is. Refused is a
  quiet grey, expired a grey outline (nobody said no, it went stale), and the
  one outcome nobody wanted is red.
*/
export const MARK: Record<Fate, string> = {
  applied: "bg-ad-accent",
  open: "border border-ad-accent bg-ad-accent-tint",
  refused: "bg-ad-mark-refused",
  expired: "border border-ad-mark-refused bg-transparent",
  undone: "bg-ad-negative",
};

/* The order the segments stack, from the baseline up: the main data first. */
const STACK: Fate[] = ["applied", "open", "refused", "expired", "undone"];

export type Tally = Record<Fate, number>;

export function tallyOf(counts: Record<string, number>): Tally {
  const out: Tally = { applied: 0, open: 0, refused: 0, expired: 0, undone: 0 };
  for (const [status, n] of Object.entries(counts)) out[fateOf(status)] += n;
  return out;
}

/* The series' own totals, so the legend can never disagree with its columns. */
export function totalsOf(series: Series): Tally {
  const out: Tally = { applied: 0, open: 0, refused: 0, expired: 0, undone: 0 };
  for (const point of series.points) {
    const one = tallyOf(point.counts);
    for (const key of STACK) out[key] += one[key];
  }
  return out;
}

function labelOf(series: Series, at: number): string {
  const start = series.points[at]?.start ?? null;
  return series.step === "hour" ? clock(start) : dayOf(start);
}

/*
  Which columns get an x label. One step all the way, chosen from the end so
  today is always named; by the hour, the round six-hour marks.
*/
function labelled(series: Series): Set<number> {
  const n = series.points.length;
  const out = new Set<number>();
  if (series.step === "hour") {
    series.points.forEach((p, i) => {
      if (new Date(p.start).getUTCHours() % 6 === 0) out.add(i);
    });
    return out;
  }
  const step = n <= 8 ? 1 : n <= 16 ? 2 : n <= 35 ? 5 : n <= 70 ? 10 : 15;
  for (let i = n - 1; i >= 0; i -= step) out.add(i);
  return out;
}

export function ProposalColumns({
  series,
  height = 188,
  fill = false,
}: {
  series: Series;
  height?: number;
  /* Take the panel's remaining height rather than a fixed one. */
  fill?: boolean;
}) {
  const tallies = series.points.map((p) => tallyOf(p.counts));
  const totals = tallies.map((t) => STACK.reduce((n, k) => n + t[k], 0));
  const max = Math.max(0, ...totals);
  /*
    An empty series is drawn as its zero line and its days, never on a padded
    scale: four empty gridlines would invent a range nothing reached.
  */
  const yt = max ? ticks(max) : [0];
  const top = yt[yt.length - 1] || 1;
  const named = labelled(series);
  const n = series.points.length;
  const gap = n > 40 ? 1 : n > 20 ? 2 : 6;
  const busiest = totals.indexOf(max);

  return (
    <figure className={`ad-chart m-0 ${fill ? "flex min-h-0 flex-1 flex-col" : ""}`}>
      <div
        className={`relative ${fill ? "flex min-h-0 flex-1 flex-col" : ""}`}
        role="img"
        aria-label={
          max
            ? `${count(totals.reduce((a, b) => a + b, 0))} changes proposed, ${labelOf(series, 0)} to ${labelOf(series, n - 1)}; the busiest ${series.step} was ${labelOf(series, busiest)} with ${count(max)}.`
            : `Nothing proposed between ${labelOf(series, 0)} and ${labelOf(series, n - 1)}.`
        }
      >
        {/* The y scale: its own lane on the left, so a label never sits on a column. */}
        <div
          className={fill ? "flex min-h-[180px] flex-1" : "flex"}
          style={fill ? undefined : { height }}
        >
          <div className="relative w-8 flex-none">
            {yt.map((v) => (
              <span
                key={v}
                className="ad-num text-ad-faint absolute right-2 -translate-y-1/2 text-[11px] leading-none"
                style={{ top: `${(1 - v / top) * 100}%` }}
              >
                {count(v)}
              </span>
            ))}
          </div>
          <div className="relative min-w-0 flex-1">
            {yt.map((v) => (
              <span
                key={v}
                aria-hidden
                className={`absolute right-0 left-0 h-px ${v === 0 ? "bg-ad-control" : "bg-ad-grid"}`}
                style={{ top: `${(1 - v / top) * 100}%` }}
              />
            ))}
            {!max ? (
              /*
                Zero proposals is a signal, not a rest: on a platform with
                connected accounts it usually means the nightly pass did not
                run.
              */
              <p className="text-ad-muted absolute top-2 left-4 max-w-[52ch] text-[13px] leading-[20px]">
                Otto proposed nothing in this window. With accounts connected that is unusual:{" "}
                <Link href="/admin/jobs" className="text-ad-accent hover:text-ad-text font-medium">
                  check the nightly pass ran
                </Link>
                .
              </p>
            ) : null}
            <div className="absolute inset-0 flex items-end" style={{ gap }}>
              {tallies.map((one, i) => (
                <div
                  key={series.points[i].start}
                  className="flex h-full min-w-0 flex-1 flex-col-reverse"
                  title={
                    totals[i]
                      ? `${labelOf(series, i)}: ${count(totals[i])} proposed. ${STACK.filter(
                          (k) => one[k],
                        )
                          .map(
                            (k) =>
                              `${count(one[k])} ${FATES.find((f) => f.key === k)!.label.toLowerCase()}`,
                          )
                          .join(", ")}.`
                      : `${labelOf(series, i)}: nothing proposed.`
                  }
                >
                  {STACK.map((k) =>
                    one[k] ? (
                      <span
                        key={k}
                        className={`block w-full flex-none ${MARK[k]}`}
                        style={{
                          height: `${(one[k] / top) * 100}%`,
                          // A 1px seam between stacked parts, in the panel's own colour.
                          boxShadow: "inset 0 -1px 0 var(--ad-surface)",
                        }}
                      />
                    ) : null,
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/*
          X labels, one step, today named in ink. The last label is pulled
          inside the plot from the right and the first from the left, so
          neither runs past the panel's edge. On a phone every other label
          drops, counted from today, so the step survives.
        */}
        <div className="mt-2 flex pl-8" style={{ gap }} aria-hidden>
          {series.points.map((p, i) => {
            if (!named.has(i)) return <div key={p.start} className="h-4 min-w-0 flex-1" />;
            const order = [...named].sort((a, b) => b - a).indexOf(i);
            const place =
              i === n - 1 ? "right-0" : i === 0 ? "left-0" : "left-1/2 -translate-x-1/2";
            return (
              <div key={p.start} className="relative h-4 min-w-0 flex-1">
                <span
                  className={`ad-num absolute top-0 text-[11px] leading-4 whitespace-nowrap ${place} ${
                    i === n - 1 ? "text-ad-text" : "text-ad-faint"
                  } ${order % 2 === 1 ? "max-sm:hidden" : ""}`}
                >
                  {labelOf(series, i)}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </figure>
  );
}

/* The legend as a small table: each fate's mark, its name and its total. */
export function FateLegend({ totals }: { totals: Tally }) {
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-2">
      {STACK.map((k) => (
        <li key={k} className="flex items-center gap-2 text-[13px] leading-[20px]">
          <span aria-hidden className={`h-2.5 w-2.5 flex-none rounded-[2px] ${MARK[k]}`} />
          <span className="text-ad-muted">{FATES.find((f) => f.key === k)!.label}</span>
          <span className={`ad-num ${totals[k] ? "text-ad-text" : "text-ad-faint"}`}>
            {count(totals[k])}
          </span>
        </li>
      ))}
    </ul>
  );
}

/* ---------- the run strip ---------- */

type RunKind = "finished" | "failed" | "stuck" | "running";

function kindOf(run: JobRun): RunKind {
  if (run.stuck) return "stuck";
  if (run.status === "failed") return "failed";
  if (run.took_seconds === null) return "running";
  return "finished";
}

const RUN_MARK: Record<RunKind, string> = {
  finished: "bg-ad-accent",
  failed: "bg-ad-negative",
  stuck: "bg-ad-warning",
  running: "border border-ad-accent bg-transparent",
};

const RUN_WORDS: Record<RunKind, string> = {
  finished: "Finished",
  failed: "Failed",
  stuck: "Never finished",
  running: "Running",
};

/*
  Every recent run as one mark, oldest on the left and the newest at the
  right edge, so a gap in the heartbeat or a run of red reads at a glance.
  The marks are runs, not time: the strip shows what happened in order, and
  the table under it says when.
*/
export function RunStrip({ runs }: { runs: JobRun[] }) {
  const ordered = [...runs].reverse();
  const tally = ordered.reduce<Record<RunKind, number>>(
    (all, one) => {
      all[kindOf(one)] += 1;
      return all;
    },
    { finished: 0, failed: 0, stuck: 0, running: 0 },
  );
  const kinds = (Object.keys(RUN_WORDS) as RunKind[]).filter((k) => tally[k]);
  return (
    <figure className="ad-strip m-0">
      <div
        className="flex h-8 items-stretch gap-[2px]"
        role="img"
        aria-label={`The last ${ordered.length} runs, oldest first: ${kinds
          .map((k) => `${tally[k]} ${RUN_WORDS[k].toLowerCase()}`)
          .join(", ")}.`}
      >
        {ordered.map((one) => (
          <span
            key={one.id}
            title={`${one.kind} ${one.customer_id ? `on ${one.customer_id}` : ""}, ${RUN_WORDS[kindOf(one)].toLowerCase()}, ${dayOf(one.started_at)} ${clock(one.started_at)} UTC`}
            className={`block max-w-[18px] min-w-[2px] flex-1 rounded-[1px] ${RUN_MARK[kindOf(one)]}`}
          />
        ))}
      </div>
      <figcaption className="mt-3 flex flex-wrap items-center justify-between gap-x-5 gap-y-2">
        <ul className="flex flex-wrap gap-x-5 gap-y-2">
          {kinds.map((k) => (
            <li key={k} className="flex items-center gap-2 text-[13px] leading-[20px]">
              <span aria-hidden className={`h-2.5 w-1.5 flex-none rounded-[1px] ${RUN_MARK[k]}`} />
              <span className="text-ad-muted">{RUN_WORDS[k]}</span>
              <span className="ad-num text-ad-text">{count(tally[k])}</span>
            </li>
          ))}
        </ul>
        <span className="text-ad-faint text-[13px] leading-[20px]">Oldest on the left</span>
      </figcaption>
    </figure>
  );
}
