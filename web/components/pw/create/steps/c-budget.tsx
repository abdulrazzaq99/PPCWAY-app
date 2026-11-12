"use client";

import { Input } from "@/components/ui/field";
import type { Spec } from "@/lib/creation";
import type { StepProps } from "../editor";
import { Card, Choice, Labelled, Note, NumberBox, money } from "../kit";
import { dateWords } from "./a-parts";

/*
  The budget, on the bidding step: Google's Demand Gen flow asks for it on
  "Bidding and budget", and PPCWay does the same for Display, Shopping and
  App, which have no budget step of their own. A daily budget, or a total
  for the whole campaign between its dates (App takes daily only). The
  dates are the campaign's own, the same ones Campaign settings shows.
*/

type Budget = Spec["budget"];

function days(start: string | null, end: string | null): number | null {
  if (!start || !end) return null;
  const a = Date.parse(`${start}T00:00:00Z`);
  const b = Date.parse(`${end}T00:00:00Z`);
  if (Number.isNaN(a) || Number.isNaN(b)) return null;
  return Math.round((b - a) / 86_400_000) + 1;
}

export function BudgetCard({ spec, change }: Pick<StepProps, "spec" | "change">) {
  const budget = spec.budget;
  const set = (patch: Partial<Budget>) => change("budget", { ...budget, ...patch });
  const cur = spec.currency;
  const app = spec.type === "APP";
  const dg = spec.type === "DEMAND_GEN";
  const daily = app || budget.type === "daily";
  const amount = budget.amount;
  const dates = spec.dates;
  const span = days(dates.start, dates.end);
  const cpa =
    dg && spec.bidding.focus === "conversions" && spec.bidding.set_target
      ? spec.bidding.target_cpa
      : null;
  const label = daily ? "Average daily budget" : "Campaign total budget";

  return (
    <Card
      title="Budget"
      help={
        app
          ? "App campaigns take a daily budget."
          : "Set an average daily budget, or one amount for the whole campaign."
      }
    >
      <div className="flex flex-col gap-4 p-6">
        {app ? (
          <p className="text-pw-ink-600 text-[13px] leading-[18px]">
            Google spends it across Google Search, Google Play, YouTube, Discover and the Display
            Network, wherever it finds the people most likely to act.
          </p>
        ) : (
          <fieldset className="flex flex-col gap-4">
            <legend className="sr-only">Budget type</legend>
            <Choice
              name="budget-type"
              checked={budget.type === "daily"}
              onChange={() => set({ type: "daily" })}
              help="Set your average daily budget for this campaign."
            >
              Daily budget
            </Choice>
            <Choice
              name="budget-type"
              checked={budget.type === "total"}
              onChange={() => set({ type: "total" })}
              help="Set one amount for the whole campaign, spent between its start and end dates."
            >
              Campaign total budget
            </Choice>
          </fieldset>
        )}

        <Labelled label={label} className="sm:w-[260px]">
          <NumberBox
            value={amount > 0 ? amount : null}
            // An App campaign saved with a total budget becomes daily as soon as an amount is typed.
            onChange={(v) => set(app ? { amount: v ?? 0, type: "daily" } : { amount: v ?? 0 })}
            unit={cur}
            min={0.01}
            placeholder={daily ? "20.00" : "600.00"}
            ariaLabel={label}
          />
        </Labelled>

        {app && budget.type === "total" ? (
          <Note tone="warn">
            This draft has a campaign total budget, which App campaigns don&apos;t take. Type the
            daily amount above and it becomes a daily budget.
          </Note>
        ) : null}

        {daily ? (
          <p className="text-pw-ink-600 text-[13px] leading-[18px]">
            {amount > 0
              ? `On a busy day Google may spend up to ${money(amount * 2, cur)}, twice your budget. Over a month it never charges more than ${money(amount * 30.4, cur)}, which is 30.4 times it.`
              : "On a busy day Google may spend up to twice your daily budget. Over a month it never charges more than 30.4 times it."}
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            <p className="text-pw-ink-600 text-[13px] leading-[18px]">
              A campaign total budget needs a start and an end date. Google spends it across those
              days, more on the days it expects to do best.
            </p>
            <div className="grid gap-3 sm:max-w-[520px] sm:grid-cols-2">
              <Labelled label="Start date" hint="Empty starts it when published.">
                <Input
                  type="date"
                  aria-label="Start date"
                  value={dates.start ?? ""}
                  onChange={(e) => change("dates", { ...dates, start: e.target.value || null })}
                />
              </Labelled>
              <Labelled label="End date">
                <Input
                  type="date"
                  aria-label="End date"
                  value={dates.end ?? ""}
                  min={dates.start ?? undefined}
                  onChange={(e) => change("dates", { ...dates, end: e.target.value || null })}
                />
              </Labelled>
            </div>
            <p className="text-pw-ink-500 text-[13px] leading-[18px]">
              {dates.end
                ? `Spent from ${dates.start ? dateWords(dates.start) : "the day it is published"} to the end of ${dateWords(dates.end)}${span ? `, ${span} days` : ""}. `
                : ""}
              {dg
                ? "Google takes a Demand Gen total budget for 7 days to 1 year."
                : "Google recommends 3 to 90 days."}{" "}
              The budget type can&apos;t change once the campaign has started.
            </p>
            {dg && span !== null && (span < 7 || span > 366) ? (
              <Note tone="warn">
                This campaign runs {span} {span === 1 ? "day" : "days"}. A Demand Gen total budget
                needs 7 days to 1 year between its dates.
              </Note>
            ) : null}
          </div>
        )}

        {dg ? (
          <p className="text-pw-ink-500 text-[13px] leading-[18px]">
            {daily
              ? "Google's minimum daily budget for Demand Gen is 5 US dollars, or about the same in your currency."
              : "Demand Gen needs a budget of its own, so shared budgets aren't offered."}
            {cpa
              ? ` Google suggests a daily budget of at least 10 times your target CPA: with ${money(cpa, cur)}, that is ${money(cpa * 10, cur)} a day.`
              : ""}
          </p>
        ) : null}
      </div>
    </Card>
  );
}
