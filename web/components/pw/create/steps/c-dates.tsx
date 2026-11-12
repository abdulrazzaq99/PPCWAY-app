"use client";

import { useState } from "react";
import { Input } from "@/components/ui/field";
import type { Spec } from "@/lib/creation";
import { Choice, Labelled } from "../kit";
import { dateWords } from "./a-parts";

/*
  The "Start and end dates" row, which every campaign type has. It lived in
  `settings.tsx` and moved here unchanged so the Demand Gen, Display,
  Shopping and App settings can use it too.
*/

export function datesSummary(d: Spec["dates"]): string {
  const start = d.start ? `Starts ${dateWords(d.start)}` : "Starts when published";
  return `${start}; ${d.end ? `ends ${dateWords(d.end)}` : "no end date"}`;
}

/*
  Start and end dates. An empty start, or one today or earlier, starts the
  campaign the moment it is published; Google refuses a start in the past.
  The end is "None" or a date, and a campaign total budget needs one.
*/
export function DatesEditor({
  dates,
  onChange,
  totalBudget,
}: {
  dates: Spec["dates"];
  onChange: (next: Spec["dates"]) => void;
  totalBudget: boolean;
}) {
  const [ending, setEnding] = useState(dates.end !== null);
  return (
    <div className="flex flex-col gap-4">
      <Labelled
        label="Start date"
        hint="Leave it empty to start as soon as the campaign is published."
        className="sm:w-[240px]"
      >
        <Input
          type="date"
          aria-label="Start date"
          value={dates.start ?? ""}
          onChange={(e) => onChange({ ...dates, start: e.target.value || null })}
        />
      </Labelled>
      <fieldset className="flex flex-col gap-3">
        <legend className="text-pw-ink mb-2 text-[13px] font-semibold">End date</legend>
        <Choice
          name="end-date"
          checked={!ending}
          onChange={() => {
            setEnding(false);
            onChange({ ...dates, end: null });
          }}
        >
          None
        </Choice>
        <Choice name="end-date" checked={ending} onChange={() => setEnding(true)}>
          Choose a date
        </Choice>
        {ending ? (
          <div className="sm:w-[240px] sm:pl-7">
            <Input
              type="date"
              aria-label="End date"
              value={dates.end ?? ""}
              min={dates.start ?? undefined}
              onChange={(e) => onChange({ ...dates, end: e.target.value || null })}
            />
          </div>
        ) : null}
      </fieldset>
      <p className="text-pw-ink-500 text-[13px] leading-[18px]">
        Dates are in the account&apos;s time zone. The campaign runs to the end of its last day.
        {totalBudget && !dates.end ? " A campaign total budget needs an end date." : ""}
      </p>
    </div>
  );
}
