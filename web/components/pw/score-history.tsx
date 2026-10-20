import Link from "next/link";
import { Chip, PwCard } from "@/components/pw/shell";
import type { Changed, Point } from "@/lib/audit";

/*
  The score over time, and what moved since last time.

  The markers are the point of the line. A dot is filled where a check went from
  "needs you" to "good", so an owner can see the day the work landed, and
  hollowed where one went the other way — which is how a redesign that quietly
  dropped the conversion tag gets noticed in a day instead of a quarter.
*/
const WIDTH = 560;
const HEIGHT = 120;
const PAD = 8;

function place(points: Point[]): { x: number; y: number; point: Point }[] {
  const scored = points.filter((p) => p.score !== null);
  if (scored.length === 0) return [];
  const span = Math.max(1, scored.length - 1);
  return scored.map((point, i) => ({
    x: PAD + (i / span) * (WIDTH - PAD * 2),
    y: PAD + (1 - (point.score ?? 0) / 100) * (HEIGHT - PAD * 2),
    point,
  }));
}

function when(at: string): string {
  return new Date(at).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function ScoreOverTime({ points }: { points: Point[] }) {
  const dots = place(points);
  const first = dots[0];
  const last = dots[dots.length - 1];

  if (dots.length < 2) {
    return (
      <PwCard className="p-6">
        <h2 className="text-[17px] leading-[22px] font-semibold">Score over time</h2>
        <p className="text-pw-ink-500 mt-3 text-[15px] leading-[23px]">
          One reading so far. The audit now re-runs on its own every night, so the line appears
          tomorrow and every fix shows up on it as a marker.
        </p>
      </PwCard>
    );
  }

  const path = dots.map((d) => `${d.x.toFixed(1)},${d.y.toFixed(1)}`).join(" ");
  const moved = dots.filter((d) => d.point.fixed.length || d.point.broke.length);

  return (
    <PwCard className="p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="text-[17px] leading-[22px] font-semibold">Score over time</h2>
        <p className="text-pw-ink-400 text-[12px]">
          {dots.length} readings · {when(first.point.at)} to {when(last.point.at)}
        </p>
      </div>

      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="mt-4 h-[120px] w-full"
        role="img"
        aria-label={`Visibility score from ${first.point.score} to ${last.point.score} over ${dots.length} readings.`}
      >
        <line
          x1={PAD}
          x2={WIDTH - PAD}
          y1={HEIGHT - PAD}
          y2={HEIGHT - PAD}
          stroke="currentColor"
          className="text-pw-divider"
        />
        <polyline
          points={path}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="text-pw-blue"
        />
        {dots.map((d) => (
          <circle
            key={d.point.run_id}
            cx={d.x}
            cy={d.y}
            r={d.point.fixed.length || d.point.broke.length ? 5 : 3}
            className={
              d.point.broke.length
                ? "text-pw-bad"
                : d.point.fixed.length
                  ? "text-pw-good-ink"
                  : "text-pw-blue"
            }
            fill="currentColor"
          />
        ))}
      </svg>

      <div className="text-pw-ink-400 flex justify-between text-[12px]">
        <span>{when(first.point.at)}</span>
        <span className="pw-num">
          {first.point.score} → {last.point.score}
        </span>
        <span>{when(last.point.at)}</span>
      </div>

      {moved.length ? (
        <ul className="divide-pw-divider mt-4 divide-y">
          {moved
            .slice(-4)
            .reverse()
            .map((d) => (
              <li key={d.point.run_id} className="flex flex-wrap items-center gap-2 py-2">
                <span className="text-pw-ink-400 w-[70px] shrink-0 text-[12px]">
                  {when(d.point.at)}
                </span>
                {d.point.fixed.map((title) => (
                  <Chip key={title} tone="good">
                    Fixed: {title}
                  </Chip>
                ))}
                {d.point.broke.map((title) => (
                  <Chip key={title} tone="bad">
                    Broke: {title}
                  </Chip>
                ))}
              </li>
            ))}
        </ul>
      ) : (
        <p className="text-pw-ink-500 mt-4 text-[14px] leading-[21px]">
          Nothing has been fixed or broken across these readings. The line is flat because the
          website has not changed.
        </p>
      )}
    </PwCard>
  );
}

export function WhatChanged({ changed, site }: { changed: Changed | null; site: string }) {
  if (!changed) return null;
  const plain = site.replace(/^https?:\/\//, "").replace(/\/$/, "");

  if (changed.first) {
    return (
      <PwCard className="p-5 sm:p-6">
        <h2 className="text-[17px] leading-[22px] font-semibold">What changed since last time</h2>
        <p className="text-pw-ink-500 mt-2 text-[15px] leading-[23px]">
          This is the first reading of {plain}, so there is nothing to compare it with yet. From
          tomorrow this panel says what moved, in both directions.
        </p>
      </PwCard>
    );
  }

  return (
    <PwCard className="p-5 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="text-[17px] leading-[22px] font-semibold">What changed since last time</h2>
        <p className="text-pw-ink-400 text-[12px]">
          {new Date(changed.before_at).toLocaleDateString()} to{" "}
          {new Date(changed.at).toLocaleDateString()}
        </p>
      </div>

      {changed.quiet ? (
        <p className="text-pw-ink-500 mt-2 text-[15px] leading-[23px]">
          Nothing moved either way. The score is still {changed.score}
          {changed.still.length
            ? `, and ${changed.still.length} ${changed.still.length === 1 ? "thing is" : "things are"} still waiting.`
            : "."}
        </p>
      ) : (
        <ul className="divide-pw-divider mt-3 divide-y">
          {changed.broke.map((moved) => (
            <li key={moved.key} className="flex flex-col gap-1 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <Chip tone="bad">Stopped working</Chip>
                <span className="text-[15px] font-semibold">{moved.title}</span>
              </div>
              <p className="text-pw-ink-500 text-[14px] leading-[21px]">{moved.summary}</p>
            </li>
          ))}
          {changed.fixed.map((moved) => (
            <li key={moved.key} className="flex flex-wrap items-center gap-2 py-3">
              <Chip tone="good">Fixed</Chip>
              <span className="text-[15px] font-semibold">{moved.title}</span>
            </li>
          ))}
        </ul>
      )}

      {changed.still.length && !changed.quiet ? (
        <p className="text-pw-ink-500 mt-3 text-[14px] leading-[21px]">
          Still waiting: {changed.still.map((m) => m.title).join(" · ")}
        </p>
      ) : null}

      <Link href="/audit/mine" className="text-pw-blue mt-3 inline-block text-[14px] font-semibold">
        Every reading →
      </Link>
    </PwCard>
  );
}
