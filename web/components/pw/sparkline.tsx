import type { AdsDay } from "@/lib/ads";

/*
  The trend on a row, as the handoff draws it: one bar a day, no axis, no
  numbers. It answers "which way is this going" at a glance and nothing else,
  which is the only question a table row has room for.

  Bars rather than a line, because a day with nothing in it should read as
  nothing rather than as a line passing through zero.
*/
export function Sparkline({
  days,
  by = "leads",
  label,
  className = "",
}: {
  days: AdsDay[] | undefined;
  by?: "leads" | "cost";
  label: string;
  className?: string;
}) {
  const series = days ?? [];
  if (series.length === 0) {
    return <span className="text-pw-ink-400 text-[13px]">—</span>;
  }
  const value = (d: AdsDay) => (by === "leads" ? d.leads : d.cost);
  const peak = Math.max(...series.map(value));
  // Nothing happened on any day, so a row of flat stubs would be a lie dressed
  // as a chart. Say it in a word instead.
  if (peak <= 0) {
    return <span className="text-pw-ink-400 text-[13px]">{by === "leads" ? "none" : "—"}</span>;
  }
  return (
    <span
      role="img"
      aria-label={label}
      className={`flex h-[26px] w-[120px] items-end gap-[1px] ${className}`}
    >
      {series.map((day) => (
        <span
          key={day.date}
          className="bg-pw-blue-light flex-1 rounded-t-[2px]"
          style={{ height: `${Math.max(6, (value(day) / peak) * 100)}%` }}
        />
      ))}
    </span>
  );
}
