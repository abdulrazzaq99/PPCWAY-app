"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { call, said, type Spec } from "@/lib/creation";
import type { StepProps } from "../editor";
import { Card, Choice, Labelled, Note, NumberBox, Problems, money } from "../kit";
import { Act, Select, dateWords, useShared } from "./a-parts";

/*
  Google's budget step: a daily budget, or a total for the whole campaign
  between its dates, with Google's recommended amounts and what a budget
  buys. Google's recommendation is built for a campaign that does not exist
  yet; the click forecast is Keyword Planner's, for Search keywords only.
  Either may have nothing to say for a new account, and then says why.
  A Search campaign may use an existing shared budget instead; Performance
  Max needs its own.
*/

type Budget = Spec["budget"];
type Option = {
  amount: number;
  clicks: number | null;
  conversions: number | null;
  cost: number | null;
};
type Forecast = {
  clicks?: number | null;
  cost?: number | null;
  average_cpc?: number | null;
  conversions?: number | null;
  average_cpa?: number | null;
  reason?: string;
};
type Advice = {
  recommendation?: { options?: Option[]; recommended?: number | null; reason?: string };
  forecast?: Forecast;
};

export function StepBudget({ draft, spec, change, problems, go, flush }: StepProps) {
  const budget = spec.budget;
  const set = (patch: Partial<Budget>) => change("budget", { ...budget, ...patch });
  const search = spec.type === "SEARCH";
  const pmax = spec.type === "PERFORMANCE_MAX";
  const cur = spec.currency;
  const shared = Boolean(budget.shared);
  const amount = budget.amount;
  const [advice, setAdvice] = useState<{ said: Advice; at: number } | null>(null);
  const [asking, setAsking] = useState(false);
  const [trouble, setTrouble] = useState("");

  async function ask() {
    setAsking(true);
    setTrouble("");
    // Google reads the saved campaign, so anything typed goes first.
    if (!(await flush())) {
      setAsking(false);
      setTrouble("The draft could not be saved, so Google was not asked.");
      return;
    }
    const { ok, data } = await call<Advice>(`v2/${draft.id}/budget`, {});
    setAsking(false);
    if (!ok) {
      setTrouble(said(data, "Google could not suggest a budget just now."));
      return;
    }
    setAdvice({ said: data, at: amount });
  }

  const span = days(spec.dates.start, spec.dates.end);
  const tinyForAiMax = search && spec.ai_max.enabled && amount > 0 && amount < 5;
  const cpa =
    spec.bidding.set_target && spec.bidding.focus === "conversions"
      ? spec.bidding.target_cpa
      : null;

  return (
    <div className="flex flex-col gap-5">
      {/* The AI Max advice is said in full below, beside the amount. */}
      <Problems items={problems.filter((p) => !p.words.startsWith("AI Max"))} />

      <Card title="Budget">
        <fieldset
          disabled={shared}
          className={cn("flex flex-col gap-4 p-6", shared && "opacity-60")}
        >
          <legend className="sr-only">Budget type and amount</legend>
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

          <Labelled
            label={budget.type === "daily" ? "Average daily budget" : "Campaign total budget"}
            className="sm:w-[260px]"
          >
            <NumberBox
              value={amount > 0 ? amount : null}
              onChange={(v) => set({ amount: v ?? 0 })}
              unit={cur}
              min={0.01}
              placeholder={budget.type === "daily" ? "20.00" : "600.00"}
              ariaLabel={budget.type === "daily" ? "Average daily budget" : "Campaign total budget"}
            />
          </Labelled>

          {budget.type === "daily" ? (
            <p className="text-pw-ink-600 text-[13px] leading-[18px]">
              {amount > 0
                ? `On a busy day Google may spend up to ${money(amount * 2, cur)}, twice your budget. Over a month it never charges more than ${money(amount * 30.4, cur)}, which is 30.4 times it.`
                : "On a busy day Google may spend up to twice your daily budget. Over a month it never charges more than 30.4 times it."}
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              <p className="text-pw-ink-600 text-[13px] leading-[18px]">
                {spec.dates.end
                  ? `Spent from ${spec.dates.start ? dateWords(spec.dates.start) : "the day it is published"} to the end of ${dateWords(spec.dates.end)}${span ? `, ${span} days` : ""}.`
                  : "A campaign total budget is spent between the campaign's start and end dates."}{" "}
                Google recommends 3 to 90 days. The budget type can&apos;t change once the campaign
                has started.
              </p>
              {!spec.dates.end ? (
                <Note tone="warn">
                  A campaign total budget needs an end date.{" "}
                  <button
                    type="button"
                    onClick={() => go("settings")}
                    className="font-semibold underline"
                  >
                    Set the dates in Campaign settings
                  </button>
                </Note>
              ) : span !== null && (span < 3 || span > 90) ? (
                <Note>
                  This campaign runs {span} {span === 1 ? "day" : "days"}. Google recommends 3 to 90
                  days for a campaign total budget.
                </Note>
              ) : null}
            </div>
          )}

          {tinyForAiMax ? (
            <Note tone="warn">
              AI Max works poorly on a very small budget. Google says it won&apos;t be effective
              when the campaign is limited by budget.
            </Note>
          ) : null}
          {pmax ? (
            <p className="text-pw-ink-500 text-[13px] leading-[18px]">
              Google advises a daily budget of at least 3 times your target cost per action
              {cpa
                ? `. With a target CPA of ${money(cpa, cur)}, that is at least ${money(cpa * 3, cur)} a day.`
                : "."}
            </p>
          ) : null}
        </fieldset>
        {shared ? (
          <div className="px-6 pb-6">
            <Note>
              This campaign uses the shared budget &quot;{budget.shared_name || "chosen below"}
              &quot;. Its amount is set in Google&apos;s Shared library.
            </Note>
          </div>
        ) : null}
      </Card>

      <Card
        title="Recommended budgets"
        help="Google's suggestion, from the campaign as it stands now."
      >
        <div className="flex flex-col gap-4 p-6">
          <div>
            <Button variant="secondary" onClick={ask} working={asking ? "Asking Google…" : false}>
              {advice ? "Ask Google again" : "Get Google's recommendation"}
            </Button>
          </div>
          {trouble ? <p className="text-pw-bad text-[13px]">{trouble}</p> : null}
          {advice ? (
            <AdviceView
              advice={advice.said}
              askedAt={advice.at}
              chosen={!shared && budget.type === "daily" ? amount : null}
              currency={cur}
              search={search}
              onPick={(a) =>
                set({
                  type: "daily",
                  amount: Math.round(a * 100) / 100,
                  shared: "",
                  shared_name: "",
                })
              }
            />
          ) : (
            <p className="text-pw-ink-500 text-[13px] leading-[18px]">
              Google looks at your keywords, locations and bidding, and suggests daily amounts with
              what it expects each to bring in.
            </p>
          )}
        </div>
      </Card>

      {search ? (
        <Card title="Shared budget" help="One budget that several campaigns spend from.">
          <div className="p-6">
            <SharedBudget budget={budget} set={set} currency={cur} />
          </div>
        </Card>
      ) : (
        <p className="text-pw-ink-500 text-[13px]">
          Performance Max needs a budget of its own, so shared budgets aren&apos;t offered.
        </p>
      )}
    </div>
  );
}

function days(start: string | null, end: string | null): number | null {
  if (!end) return null;
  if (!start) return null;
  const a = Date.parse(`${start}T00:00:00Z`);
  const b = Date.parse(`${end}T00:00:00Z`);
  if (Number.isNaN(a) || Number.isNaN(b)) return null;
  return Math.round((b - a) / 86_400_000) + 1;
}

/** A forecast figure as people say it. */
function about(n: number): string {
  if (n >= 100) return Math.round(n).toLocaleString();
  if (n >= 10) return String(Math.round(n));
  return String(Math.round(n * 10) / 10);
}

function estimate(o: Option, currency: string): string {
  const what: string[] = [];
  if (o.clicks !== null) what.push(`${about(o.clicks)} clicks`);
  if (o.conversions !== null) what.push(`${about(o.conversions)} conversions`);
  if (!what.length && o.cost === null) return "Google gave no estimate for this amount.";
  const cost =
    o.cost !== null ? `${what.length ? ", " : ""}costing about ${money(o.cost, currency)}` : "";
  return `Google expects ${what.length ? `about ${what.join(" and ")}` : "it to spend"}${cost}.`;
}

function forecastWords(f: Forecast, currency: string): string[] {
  const out: string[] = [];
  if (typeof f.clicks === "number") {
    const clicks =
      f.clicks < 1 ? "Fewer than one click a day" : `About ${about(f.clicks)} clicks a day`;
    const cost = typeof f.cost === "number" ? ` for about ${money(f.cost, currency)}` : "";
    const each =
      typeof f.average_cpc === "number"
        ? `, at about ${money(f.average_cpc, currency)} a click`
        : "";
    out.push(`${clicks}${cost}${each}.`);
  }
  if (typeof f.conversions === "number" && f.conversions > 0) {
    const each =
      typeof f.average_cpa === "number" ? `, at about ${money(f.average_cpa, currency)} each` : "";
    out.push(`About ${about(f.conversions)} conversions a day${each}.`);
  }
  return out;
}

function AdviceView({
  advice,
  askedAt,
  chosen,
  currency,
  search,
  onPick,
}: {
  advice: Advice;
  askedAt: number;
  chosen: number | null;
  currency: string;
  search: boolean;
  onPick: (amount: number) => void;
}) {
  const rec = advice.recommendation ?? {};
  const options = [...(rec.options ?? [])];
  const recommended = rec.recommended ?? null;
  // Google can name a recommended amount without listing it as an option.
  if (recommended !== null && !options.some((o) => Math.abs(o.amount - recommended) < 0.01)) {
    options.push({ amount: recommended, clicks: null, conversions: null, cost: null });
    options.sort((x, y) => x.amount - y.amount);
  }
  const forecast = advice.forecast ?? {};
  const words = forecastWords(forecast, currency);

  return (
    <div className="flex flex-col gap-4">
      {options.length ? (
        <div
          role="radiogroup"
          aria-label="Recommended budgets"
          className="grid gap-3 sm:grid-cols-3"
        >
          {options.map((o) => {
            const on = chosen !== null && Math.abs(chosen - o.amount) < 0.01;
            const best = recommended !== null && Math.abs(recommended - o.amount) < 0.01;
            return (
              <button
                key={o.amount}
                type="button"
                role="radio"
                aria-checked={on}
                onClick={() => onPick(o.amount)}
                className={cn(
                  "flex flex-col items-start gap-1 rounded-[14px] border p-4 text-left transition-[border-color,background-color]",
                  on
                    ? "border-pw-blue bg-pw-blue-tint border-2 p-[15px]"
                    : "border-pw-border bg-pw-card hover:border-pw-border-strong",
                )}
              >
                {best ? (
                  <span className="text-pw-blue text-[12px] font-semibold">Recommended</span>
                ) : null}
                <span className="text-pw-ink text-[18px] font-semibold">
                  {money(o.amount, currency)}
                  <span className="text-pw-ink-500 text-[13px] font-normal"> a day</span>
                </span>
                <span className="text-pw-ink-600 text-[13px] leading-[18px]">
                  {estimate(o, currency)}
                </span>
              </button>
            );
          })}
        </div>
      ) : (
        <Note>{rec.reason || "Google has no budget suggestion for this campaign yet."}</Note>
      )}
      {options.length ? (
        <p className="text-pw-ink-500 text-[12px] leading-[16px]">
          Choosing an amount makes it the campaign&apos;s daily budget. Google doesn&apos;t say what
          period its estimates cover.
        </p>
      ) : null}

      {search ? (
        <div className="bg-pw-muted flex flex-col gap-1 rounded-[12px] px-4 py-3 text-[14px] leading-[20px]">
          {words.length ? (
            <>
              <p className="text-pw-ink font-semibold">
                With your keywords and {money(askedAt, currency)} a day, Google&apos;s Keyword
                Planner forecasts:
              </p>
              {words.map((w) => (
                <p key={w} className="text-pw-ink-700">
                  {w}
                </p>
              ))}
            </>
          ) : (
            <p className="text-pw-ink-700">
              {forecast.reason ||
                (askedAt > 0
                  ? "Google had no click forecast for this campaign."
                  : "Google forecasts clicks once the campaign has keywords and a daily budget.")}
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}

function SharedBudget({
  budget,
  set,
  currency,
}: {
  budget: Budget;
  set: (patch: Partial<Budget>) => void;
  currency: string;
}) {
  const { shared, trouble } = useShared();
  if (trouble) return <p className="text-pw-bad text-[13px]">{trouble}</p>;
  if (!shared)
    return <p className="text-pw-ink-500 text-[13px]">Looking in your shared library…</p>;
  const known = shared.budgets.some((b) => b.resource === budget.shared);
  if (!shared.budgets.length && !budget.shared) {
    return (
      <p className="text-pw-ink-500 text-[13px]">
        This account has no shared budgets, so this campaign gets its own.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <Labelled
        label="Select a shared budget"
        hint="Choosing one replaces this campaign's own budget."
        className="sm:w-[420px]"
      >
        <Select
          aria-label="Select a shared budget"
          value={budget.shared}
          onChange={(e) => {
            const pick = shared.budgets.find((b) => b.resource === e.target.value);
            set(
              pick
                ? { shared: pick.resource, shared_name: pick.name, type: "daily" }
                : { shared: "", shared_name: "" },
            );
          }}
        >
          <option value="">Don&apos;t use a shared budget</option>
          {shared.budgets.map((b) => (
            <option key={b.resource} value={b.resource}>
              {b.name}
              {b.amount !== null && (!b.period || b.period === "DAILY")
                ? `, ${money(b.amount, currency)} a day`
                : ""}
            </option>
          ))}
          {budget.shared && !known ? (
            <option value={budget.shared}>
              {budget.shared_name || "The shared budget chosen earlier"}
            </option>
          ) : null}
        </Select>
      </Labelled>
      {budget.shared ? (
        <Act onClick={() => set({ shared: "", shared_name: "" })}>
          Use this campaign&apos;s own budget instead
        </Act>
      ) : null}
    </div>
  );
}
