"use client";

import { useId, type ReactNode } from "react";
import { Choice, Labelled, money, NumberBox } from "@/components/pw/create/kit";
import {
  DATA_DRIVEN,
  LAST_CLICK,
  type Action,
  type Kind,
  type Settings,
  type SourceKey,
  type SourceOption,
} from "./types";

/*
  A conversion action's settings, worded as Google's "Create conversion
  actions" step and its settings page word them: Value, Count, the two
  conversion windows, Attribution and Action optimization, and Call length
  for calls. The same form is used to create an action and to change one.
*/

/** Bought something: Google recommends counting every one. */
const SALE = new Set(["PURCHASE", "ADD_TO_CART", "BEGIN_CHECKOUT", "SUBSCRIBE_PAID"]);
/** Each sale has its own amount, so Google suggests different values. */
const VALUED = new Set(["PURCHASE", "SUBSCRIBE_PAID"]);
/** Steps on the way to a sale: Google suggests observing them, not bidding for them. */
const SECONDARY = new Set(["ADD_TO_CART", "BEGIN_CHECKOUT", "PAGE_VIEW"]);

/** Google's recommended settings for a new action of this source and goal. */
export function defaultsFor(category: string, option?: SourceOption): Settings {
  const call = Boolean(option?.call);
  return {
    value: VALUED.has(category) && !call ? "different" : "same",
    amount: 1,
    count: SALE.has(category) ? "every" : "one",
    click_days: 30,
    view_days: 1,
    attribution: "data_driven",
    primary: !SECONDARY.has(category),
    call_seconds: 60,
  };
}

/** An existing action's settings, as the form holds them. */
export function fromAction(a: Action): Settings {
  return {
    value: a.value.always ? "same" : "different",
    amount: a.value.default,
    count: a.counting === "ONE_PER_CLICK" ? "one" : "every",
    click_days: a.click_days,
    view_days: a.view_days,
    attribution:
      a.attribution === DATA_DRIVEN
        ? "data_driven"
        : a.attribution === LAST_CLICK
          ? "last_click"
          : "",
    primary: a.primary,
    call_seconds: a.call_seconds,
  };
}

/** What Google would refuse in these settings, said before anything is sent. */
export function settingsProblems(
  label: string,
  s: Settings,
  kind: Kind,
  only?: Set<keyof Settings>,
): string[] {
  const out: string[] = [];
  const asks = (key: keyof Settings) => !only || only.has(key);
  const most = kind.call ? 60 : 90;
  if (asks("value") || asks("amount")) {
    if (s.value === "same" && s.amount === null) {
      out.push(
        `"${label}": give the value of each conversion, or choose "Don't use a value for this conversion action".`,
      );
    }
    if (s.value !== "none" && s.amount !== null && s.amount < 0) {
      out.push(`"${label}": the value cannot be negative.`);
    }
  }
  if (asks("click_days") && (s.click_days === null || s.click_days < 1 || s.click_days > most)) {
    out.push(`"${label}": the click-through conversion window is 1 to ${most} days.`);
  }
  if (
    kind.view &&
    asks("view_days") &&
    (s.view_days === null || s.view_days < 1 || s.view_days > 30)
  ) {
    out.push(`"${label}": the view-through conversion window is 1 to 30 days.`);
  }
  if (
    kind.call &&
    asks("call_seconds") &&
    (s.call_seconds === null || s.call_seconds < 0 || s.call_seconds > 10_000)
  ) {
    out.push(`"${label}": a call counts after 0 to 10,000 seconds.`);
  }
  if (asks("attribution") && !s.attribution) {
    out.push(`"${label}": choose Data-driven or Last click attribution.`);
  }
  return out;
}

const days = (n: number | null) => (n === null ? "no" : `${n} day${n === 1 ? "" : "s"}`);

/** The settings in one line, for the closed "Settings" row. */
export function settingsLine(s: Settings, kind: Kind, currency: string): string {
  const value =
    s.value === "none"
      ? "No value"
      : s.value === "same"
        ? `${money(s.amount ?? 0, currency)} each`
        : `Different values, ${money(s.amount ?? 0, currency)} by default`;
  const parts = [
    s.primary ? "Primary" : "Secondary",
    value,
    s.count === "every" ? "Every conversion" : "One conversion",
    `${days(s.click_days)} click-through`,
  ];
  if (kind.view) parts.push(`${days(s.view_days)} view-through`);
  parts.push(s.attribution === "last_click" ? "Last click" : "Data-driven");
  if (kind.call) parts.push(`calls of ${s.call_seconds ?? 0} seconds or more`);
  return parts.join(", ");
}

function Group({ legend, children }: { legend: string; children: ReactNode }) {
  return (
    <fieldset className="flex min-w-0 flex-col gap-3">
      <legend className="text-pw-ink mb-1 text-[13px] leading-[18px] font-semibold">
        {legend}
      </legend>
      {children}
    </fieldset>
  );
}

export function ActionSettings({
  value: s,
  onChange,
  kind,
  currency,
  sourceKey,
}: {
  value: Settings;
  onChange: (next: Settings) => void;
  kind: Kind;
  currency: string;
  /** Which source a new action comes from; changes Google's advice on calls. */
  sourceKey?: SourceKey;
}) {
  const id = useId();
  const set = (patch: Partial<Settings>) => onChange({ ...s, ...patch });
  const most = kind.call ? 60 : 90;
  return (
    <div className="grid gap-6 sm:grid-cols-2">
      <Group legend="Action optimization">
        <Choice
          name={`${id}-primary`}
          checked={s.primary}
          onChange={() => set({ primary: true })}
          help="Counts in your Conversions column, and bidding aims for it."
        >
          Primary action used for bidding optimization
        </Choice>
        <Choice
          name={`${id}-primary`}
          checked={!s.primary}
          onChange={() => set({ primary: false })}
          help="Counts in All conversions only. Bidding ignores it."
        >
          Secondary action used for observation only
        </Choice>
      </Group>

      <Group legend="Value">
        <Choice
          name={`${id}-value`}
          checked={s.value === "same"}
          onChange={() => set({ value: "same", amount: s.amount ?? 1 })}
          help={
            kind.call && sourceKey !== "call_uploads"
              ? "Google gives every call the same value."
              : undefined
          }
        >
          Use the same value for each conversion
        </Choice>
        {s.value === "same" ? (
          <div className="pl-7">
            <NumberBox
              value={s.amount}
              onChange={(amount) => set({ amount })}
              unit={currency}
              min={0}
              ariaLabel="Value of each conversion"
              className="max-w-[220px]"
            />
          </div>
        ) : null}
        {kind.different ? (
          <>
            <Choice
              name={`${id}-value`}
              checked={s.value === "different"}
              onChange={() => set({ value: "different", amount: s.amount ?? 1 })}
              help="Your tag or upload sends each conversion's value. This one is used when none is sent."
            >
              Use different values for each conversion
            </Choice>
            {s.value === "different" ? (
              <div className="pl-7">
                <NumberBox
                  value={s.amount}
                  onChange={(amount) => set({ amount })}
                  unit={currency}
                  min={0}
                  ariaLabel="Default value, used when no value is sent"
                  className="max-w-[220px]"
                />
              </div>
            ) : null}
          </>
        ) : null}
        <Choice
          name={`${id}-value`}
          checked={s.value === "none"}
          onChange={() => set({ value: "none" })}
          help="Not recommended. Bidding for value then has nothing to go on."
        >
          Don&apos;t use a value for this conversion action
        </Choice>
      </Group>

      <Group legend="Count">
        <Choice
          name={`${id}-count`}
          checked={s.count === "every"}
          onChange={() => set({ count: "every" })}
          help="Recommended for purchases because every purchase is valuable."
        >
          Every
        </Choice>
        <Choice
          name={`${id}-count`}
          checked={s.count === "one"}
          onChange={() => set({ count: "one" })}
          help="Recommended for leads, sign-ups and other conversions because only the first interaction is valuable."
        >
          One
        </Choice>
      </Group>

      <Group legend="Attribution">
        <Choice
          name={`${id}-attribution`}
          checked={s.attribution === "data_driven"}
          onChange={() => set({ attribution: "data_driven" })}
          help="Recommended. Credit goes to each ad interaction by how much it helped, from this account's own data."
        >
          Data-driven
        </Choice>
        <Choice
          name={`${id}-attribution`}
          checked={s.attribution === "last_click"}
          onChange={() => set({ attribution: "last_click" })}
          help="All the credit goes to the last ad clicked."
        >
          Last click
        </Choice>
      </Group>

      <Labelled
        label="Click-through conversion window"
        hint={`How long after a click on your ad a conversion still counts. 1 to ${most} days.`}
      >
        <NumberBox
          value={s.click_days}
          onChange={(click_days) => set({ click_days })}
          unit="days"
          min={1}
          max={most}
          step={1}
          ariaLabel="Click-through conversion window in days"
          className="max-w-[220px]"
        />
      </Labelled>

      {kind.view ? (
        <Labelled
          label="View-through conversion window"
          hint="How long after someone sees your ad, without clicking, a conversion still counts. 1 to 30 days."
        >
          <NumberBox
            value={s.view_days}
            onChange={(view_days) => set({ view_days })}
            unit="days"
            min={1}
            max={30}
            step={1}
            ariaLabel="View-through conversion window in days"
            className="max-w-[220px]"
          />
        </Labelled>
      ) : null}

      {kind.call ? (
        <Labelled
          label="Call length"
          hint="A call counts as a conversion when it lasts at least this long. Google suggests 60 seconds."
        >
          <NumberBox
            value={s.call_seconds}
            onChange={(call_seconds) => set({ call_seconds })}
            unit="seconds"
            min={0}
            max={10_000}
            step={1}
            ariaLabel="Call length in seconds"
            className="max-w-[220px]"
          />
        </Labelled>
      ) : null}
    </div>
  );
}
