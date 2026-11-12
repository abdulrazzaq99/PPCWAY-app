"use client";

import { TrashIcon } from "@phosphor-icons/react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { Day, Spec } from "@/lib/creation";
import { Labelled, NumberBox } from "../kit";
import { Select } from "./a-parts";

/*
  Google's ad schedule: days and time ranges in 15-minute steps, in the
  account's time zone, up to six a day. Google's day menu also offers "All
  days", "Mondays to Fridays" and "Saturdays and Sundays"; Google keeps one
  entry per day, so picking a group adds one row for each of its days. No
  rows means ads run all day, every day.
*/

type Entry = Spec["schedule"][number];
type Minute = Entry["start_minute"];

const DAYS: Day[] = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"];

const DAY_LABEL: Record<Day, string> = {
  MONDAY: "Monday",
  TUESDAY: "Tuesday",
  WEDNESDAY: "Wednesday",
  THURSDAY: "Thursday",
  FRIDAY: "Friday",
  SATURDAY: "Saturday",
  SUNDAY: "Sunday",
};

const GROUPS: { id: string; label: string; days: Day[] }[] = [
  { id: "ALL", label: "All days", days: DAYS },
  { id: "WEEKDAYS", label: "Mondays to Fridays", days: DAYS.slice(0, 5) },
  { id: "WEEKEND", label: "Saturdays and Sundays", days: DAYS.slice(5) },
];

const PER_DAY = 6;

/** Minutes after midnight, every 15 minutes, 00:00 to 24:00. */
const TIMES = Array.from({ length: 97 }, (_, i) => i * 15);

const clock = (t: number) =>
  `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`;
const startOf = (e: Entry) => e.start_hour * 60 + e.start_minute;
const endOf = (e: Entry) => e.end_hour * 60 + e.end_minute;
const parts = (t: number) => ({ hour: Math.floor(t / 60), minute: (t % 60) as Minute });

function sorted(entries: Entry[]): Entry[] {
  return [...entries].sort(
    (a, b) => DAYS.indexOf(a.day) - DAYS.indexOf(b.day) || startOf(a) - startOf(b),
  );
}

/** The Ad schedule row's one-line summary. */
export function scheduleSummary(entries: Entry[]): string {
  if (!entries.length) return "All day";
  const first = entries[0];
  const same = entries.every((e) => startOf(e) === startOf(first) && endOf(e) === endOf(first));
  const days = DAYS.filter((d) => entries.some((e) => e.day === d));
  if (same) {
    const group = GROUPS.find(
      (g) => g.days.length === days.length && g.days.every((d) => days.includes(d)),
    );
    const which = group ? group.label : days.map((d) => DAY_LABEL[d].slice(0, 3)).join(", ");
    return `${which}, ${clock(startOf(first))} to ${clock(endOf(first))}`;
  }
  return `${entries.length} time slots across ${days.length} ${days.length === 1 ? "day" : "days"}`;
}

export function ScheduleEditor({
  entries,
  onChange,
  adjust,
  adjustApplies,
  timeZone,
}: {
  entries: Entry[];
  onChange: (next: Entry[]) => void;
  /** Search shows a bid adjustment per row; Performance Max takes none. */
  adjust: boolean;
  /** Smart Bidding ignores schedule adjustments; manual CPC and Maximize clicks use them. */
  adjustApplies: boolean;
  timeZone: string;
}) {
  const [days, setDays] = useState("ALL");
  const [from, setFrom] = useState(9 * 60);
  const [to, setTo] = useState(17 * 60);
  const used = (d: Day) => entries.filter((e) => e.day === d).length;
  const chosen = GROUPS.find((g) => g.id === days)?.days ?? [days as Day];
  const room = chosen.some((d) => used(d) < PER_DAY);

  const add = () => {
    const s = parts(from);
    const e = parts(to);
    const next = [...entries];
    for (const d of chosen) {
      if (next.filter((x) => x.day === d).length >= PER_DAY) continue;
      next.push({
        day: d,
        start_hour: s.hour,
        start_minute: s.minute,
        end_hour: e.hour,
        end_minute: e.minute,
        bid_adjustment: null,
      });
    }
    onChange(sorted(next));
  };

  const edit = (at: number, patch: Partial<Entry>) =>
    onChange(entries.map((e, i) => (i === at ? { ...e, ...patch } : e)));

  return (
    <div className="flex flex-col gap-4">
      <p className="text-pw-ink-600 text-[13px] leading-[18px]">
        {entries.length
          ? "Ads run only at these times."
          : "Ads run all day, every day. Add times to run them only then."}{" "}
        Times are in the account&apos;s time zone{timeZone ? `, ${timeZone}` : ""}.
      </p>

      {entries.length ? (
        <ul className="flex flex-col gap-3">
          {entries.map((e, at) => {
            const backwards = endOf(e) <= startOf(e);
            return (
              <li
                key={at}
                className="border-pw-border flex flex-col gap-2 rounded-[12px] border p-3"
              >
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-[1.3fr_1fr_1fr_auto] sm:items-center">
                  <Select
                    aria-label={`Day of time slot ${at + 1}`}
                    value={e.day}
                    onChange={(ev) => edit(at, { day: ev.target.value as Day })}
                    className="col-span-2 sm:col-span-1"
                  >
                    {DAYS.map((d) => (
                      <option key={d} value={d} disabled={d !== e.day && used(d) >= PER_DAY}>
                        {DAY_LABEL[d]}
                      </option>
                    ))}
                  </Select>
                  <TimeSelect
                    label={`Start of time slot ${at + 1}`}
                    value={startOf(e)}
                    last={false}
                    onChange={(t) =>
                      edit(at, { start_hour: parts(t).hour, start_minute: parts(t).minute })
                    }
                  />
                  <TimeSelect
                    label={`End of time slot ${at + 1}`}
                    value={endOf(e)}
                    last
                    onChange={(t) =>
                      edit(at, { end_hour: parts(t).hour, end_minute: parts(t).minute })
                    }
                  />
                  <button
                    type="button"
                    aria-label={`Remove time slot ${at + 1}`}
                    onClick={() => onChange(entries.filter((_, i) => i !== at))}
                    className="text-pw-ink-400 hover:text-pw-bad hover:bg-pw-muted justify-self-end rounded-full p-2"
                  >
                    <TrashIcon className="size-4" />
                  </button>
                </div>
                {adjust ? (
                  <Labelled
                    label="Bid adjustment"
                    hint="-90% to +900%. Empty means no change."
                    className="sm:w-[220px]"
                  >
                    <NumberBox
                      value={e.bid_adjustment}
                      onChange={(v) => edit(at, { bid_adjustment: v })}
                      unit="%"
                      min={-90}
                      max={900}
                      placeholder="0"
                      ariaLabel={`Bid adjustment for time slot ${at + 1}`}
                    />
                  </Labelled>
                ) : null}
                {backwards ? (
                  <p className="text-pw-bad text-[13px]">This slot ends before it starts.</p>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}

      <div className="bg-pw-muted flex flex-col gap-3 rounded-[12px] p-3">
        <p className="text-pw-ink text-[13px] font-semibold">Add times</p>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-[1.3fr_1fr_1fr_auto] sm:items-center">
          <Select
            aria-label="Days"
            value={days}
            onChange={(e) => setDays(e.target.value)}
            className="col-span-2 sm:col-span-1"
          >
            {GROUPS.map((g) => (
              <option key={g.id} value={g.id}>
                {g.label}
              </option>
            ))}
            {DAYS.map((d) => (
              <option key={d} value={d} disabled={used(d) >= PER_DAY}>
                {DAY_LABEL[d]}s
              </option>
            ))}
          </Select>
          <TimeSelect label="From" value={from} last={false} onChange={setFrom} />
          <TimeSelect label="To" value={to} last onChange={setTo} />
          <Button
            variant="secondary"
            size="sm"
            onClick={add}
            disabled={!room || to <= from}
            className="col-span-2 sm:col-span-1"
          >
            Add
          </Button>
        </div>
        {!room ? (
          <p className="text-pw-ink-500 text-[12px]">Google allows up to 6 time slots a day.</p>
        ) : null}
        {to <= from ? (
          <p className="text-pw-bad text-[12px]">The end time has to be after the start time.</p>
        ) : null}
      </div>

      {adjust && entries.length && !adjustApplies ? (
        <p className="text-pw-ink-500 text-[13px] leading-[18px]">
          Smart Bidding sets its own bids at every hour, so schedule bid adjustments are only sent
          under manual CPC or Maximize clicks.
        </p>
      ) : null}
      <p className="text-pw-ink-500 text-[13px] leading-[18px]">
        With days left out, Google still spends up to 30.4 times your daily budget in a month, and
        never more than twice it in a day.
      </p>
    </div>
  );
}

function TimeSelect({
  label,
  value,
  last,
  onChange,
}: {
  label: string;
  value: number;
  /** An end time: 00:15 to 24:00. A start time: 00:00 to 23:45. */
  last: boolean;
  onChange: (t: number) => void;
}) {
  const options = last ? TIMES.slice(1) : TIMES.slice(0, -1);
  return (
    <Select aria-label={label} value={value} onChange={(e) => onChange(Number(e.target.value))}>
      {options.map((t) => (
        <option key={t} value={t}>
          {clock(t)}
        </option>
      ))}
    </Select>
  );
}
