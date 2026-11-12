"use client";

import {
  AddressBookIcon,
  CompassIcon,
  CursorClickIcon,
  DeviceMobileIcon,
  LightningIcon,
  MagicWandIcon,
  MagnifyingGlassIcon,
  MonitorIcon,
  ShoppingCartIcon,
  SlidersHorizontalIcon,
  StorefrontIcon,
  TagIcon,
  TrashIcon,
  VideoIcon,
  YoutubeLogoIcon,
  type Icon,
} from "@phosphor-icons/react";
import Link from "next/link";
import { useState } from "react";
import { Input } from "@/components/ui/field";
import { cn } from "@/lib/cn";
import type { ConversionGoal, GoalPair, Objective, Setup, Spec } from "@/lib/creation";
import { Labelled, Note, Tick } from "./kit";

/*
  The parts of Google's step 1, shared by the "New campaign" page and the
  "Campaign type and goal" step that edits it later: the objective tiles,
  the conversion goals the campaign will bid for, the campaign types, the
  ways to reach the goal, and the name.
*/

export const OBJECTIVE_ICON: Record<Objective, Icon> = {
  sales: TagIcon,
  leads: AddressBookIcon,
  traffic: CursorClickIcon,
  awareness: YoutubeLogoIcon,
  app: DeviceMobileIcon,
  local: StorefrontIcon,
  none: SlidersHorizontalIcon,
};

export const TYPE_ICON: Record<string, Icon> = {
  SEARCH: MagnifyingGlassIcon,
  PERFORMANCE_MAX: LightningIcon,
  DEMAND_GEN: CompassIcon,
  VIDEO: VideoIcon,
  DISPLAY: MonitorIcon,
  SHOPPING: ShoppingCartIcon,
  APP: DeviceMobileIcon,
  SMART: MagicWandIcon,
};

const ORDER: Objective[] = ["sales", "leads", "traffic", "awareness", "app", "local", "none"];

export function ObjectiveTiles({
  setup,
  value,
  onChange,
}: {
  setup: Setup;
  value: Objective | null;
  onChange: (next: Objective) => void;
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Objective"
      className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
    >
      {ORDER.map((id) => {
        const o = setup.objectives[id];
        const Icon = OBJECTIVE_ICON[id];
        const on = value === id;
        return (
          <button
            key={id}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => onChange(id)}
            className={cn(
              "flex min-h-[132px] flex-col items-start gap-3 rounded-[16px] border p-4 text-left transition-[border-color,background-color]",
              on
                ? "border-pw-blue bg-pw-blue-tint border-2 p-[15px]"
                : "border-pw-border bg-pw-card hover:border-pw-border-strong",
            )}
          >
            <Icon className={cn("size-7", on ? "text-pw-blue" : "text-pw-ink-500")} />
            <span className="text-pw-ink text-[15px] leading-[20px] font-semibold">{o.label}</span>
            <span className="text-pw-ink-500 text-[13px] leading-[18px]">{o.help}</span>
          </button>
        );
      })}
    </div>
  );
}

const key = (g: { category: string; origin: string }) => `${g.category}~${g.origin}`;

/*
  "Use these conversion goals to improve <objective>": the account's default
  goals come pre-selected, and each can be removed or another added, as in
  Google's step 1. Removing or adding makes the goals campaign-specific.
*/
export function GoalsTable({
  setup,
  goals,
  onChange,
}: {
  setup: Setup;
  goals: Spec["goals"];
  onChange: (next: Spec["goals"]) => void;
}) {
  const all: ConversionGoal[] = setup.conversion?.goals ?? [];
  const available: GoalPair[] = all.map((g) => ({
    category: g.category,
    origin: g.origin,
    name: g.label,
  }));
  const defaults = all.filter((g) => g.biddable);
  const chosenKeys = new Set(goals.account_default ? defaults.map(key) : goals.chosen.map(key));
  const shown = all.filter((g) => chosenKeys.has(key(g)));
  const others = all.filter((g) => !chosenKeys.has(key(g)));
  const [adding, setAdding] = useState(false);

  const set = (keys: Set<string>) => {
    const chosen = all
      .filter((g) => keys.has(key(g)))
      .map((g) => ({ category: g.category, origin: g.origin, name: g.label }));
    const same = keys.size === defaults.length && defaults.every((g) => keys.has(key(g)));
    onChange({ account_default: same, chosen: same ? [] : chosen, available });
  };

  if (!setup.connected) return null;
  if (!all.length) {
    return (
      <Note tone="warn">
        This account has no conversion goals yet, so Google cannot bid for conversions.{" "}
        <Link href="/conversions/new" className="font-semibold underline">
          Set up conversion tracking
        </Link>{" "}
        first, as Google asks. You can still create a campaign that bids for clicks.
      </Note>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-pw-ink-600 text-[14px]">
        {goals.account_default
          ? "These are your account's default goals."
          : "These goals are set for this campaign only."}
      </p>
      <div className="border-pw-border overflow-hidden rounded-[14px] border">
        <table className="w-full text-left text-[14px]">
          <thead className="bg-pw-muted text-pw-ink-500 text-[12px] uppercase">
            <tr>
              <th className="px-4 py-2 font-semibold">Conversion goals</th>
              <th className="px-4 py-2 font-semibold">Conversion source</th>
              <th className="px-4 py-2 font-semibold">Conversion actions</th>
              <th className="w-10 px-2 py-2" />
            </tr>
          </thead>
          <tbody className="divide-pw-border divide-y">
            {shown.map((g) => (
              <tr key={key(g)}>
                <td className="text-pw-ink px-4 py-3 font-medium">
                  {g.label}
                  {g.biddable ? (
                    <span className="text-pw-ink-500 ml-2 text-[12px] font-normal">
                      (account default)
                    </span>
                  ) : null}
                </td>
                <td className="text-pw-ink-600 px-4 py-3">{g.origin_label ?? g.origin}</td>
                <td className="text-pw-ink-600 px-4 py-3">
                  {g.actions.length} action{g.actions.length === 1 ? "" : "s"}
                  {g.actions.length ? (
                    <span className="text-pw-ink-400 block truncate text-[12px]">
                      {g.actions.map((a) => a.name).join(", ")}
                    </span>
                  ) : null}
                </td>
                <td className="px-2 py-3">
                  <button
                    type="button"
                    aria-label={`Remove ${g.label}`}
                    onClick={() => {
                      const next = new Set(chosenKeys);
                      next.delete(key(g));
                      set(next);
                    }}
                    className="text-pw-ink-400 hover:text-pw-bad rounded-full p-1"
                  >
                    <TrashIcon className="size-4" />
                  </button>
                </td>
              </tr>
            ))}
            {!shown.length ? (
              <tr>
                <td colSpan={4} className="text-pw-bad px-4 py-3 text-[13px]">
                  No goal is selected. Add one, or bidding has nothing to aim for.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        {others.length ? (
          adding ? (
            <div className="flex flex-wrap gap-2">
              {others.map((g) => (
                <button
                  key={key(g)}
                  type="button"
                  onClick={() => {
                    set(new Set(chosenKeys).add(key(g)));
                    setAdding(false);
                  }}
                  className="border-pw-border hover:border-pw-blue rounded-full border px-3 py-[6px] text-[13px]"
                >
                  {g.label} · {g.origin_label ?? g.origin}
                </button>
              ))}
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setAdding(true)}
              className="text-pw-blue text-[14px] font-semibold"
            >
              + Add goal
            </button>
          )
        ) : null}
        {!goals.account_default ? (
          <button
            type="button"
            onClick={() => onChange({ account_default: true, chosen: [], available })}
            className="text-pw-blue text-[14px] font-semibold"
          >
            Use account goals
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function TypeTiles({
  setup,
  objective,
  value,
  onChange,
}: {
  setup: Setup;
  objective: Objective;
  value: string | null;
  onChange: (next: string) => void;
}) {
  const offered = setup.objectives[objective]?.types ?? [];
  return (
    <div
      role="radiogroup"
      aria-label="Campaign type"
      className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
    >
      {offered.map((id) => {
        const t = setup.types[id];
        if (!t) return null;
        const Icon = TYPE_ICON[id] ?? MagnifyingGlassIcon;
        const built = setup.built.includes(id);
        const usable = t.creatable && built;
        const on = value === id;
        return (
          <button
            key={id}
            type="button"
            role="radio"
            aria-checked={on}
            aria-disabled={!usable}
            onClick={() => usable && onChange(id)}
            className={cn(
              "flex min-h-[150px] flex-col items-start gap-2 rounded-[16px] border p-4 text-left transition-[border-color,background-color]",
              on && "border-pw-blue bg-pw-blue-tint border-2 p-[15px]",
              !on && usable && "border-pw-border bg-pw-card hover:border-pw-border-strong",
              !usable && "border-pw-border bg-pw-muted cursor-not-allowed",
            )}
          >
            <Icon
              className={cn(
                "size-7",
                on ? "text-pw-blue" : usable ? "text-pw-ink-500" : "text-pw-ink-300",
              )}
            />
            <span
              className={cn(
                "text-[15px] leading-[20px] font-semibold",
                usable ? "text-pw-ink" : "text-pw-ink-400",
              )}
            >
              {t.label}
            </span>
            <span className="text-pw-ink-500 text-[13px] leading-[18px]">{t.help}</span>
            {!t.creatable ? (
              <span className="text-pw-ink-500 mt-auto text-[12px] leading-[16px]">{t.why}</span>
            ) : !built ? (
              <span className="text-pw-warn-ink mt-auto text-[12px] leading-[16px] font-medium">
                Not in PPCWay yet. Search and Performance Max are.
              </span>
            ) : t.note ? (
              <span className="text-pw-ink-500 mt-auto text-[12px] leading-[16px]">{t.note}</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

/* "Select the ways you'd like to reach your goal". */
export function WaysToReach({
  ways,
  onChange,
  type,
}: {
  ways: Spec["ways"];
  onChange: (next: Spec["ways"]) => void;
  type: string;
}) {
  const set = (patch: Partial<Spec["ways"]>) => onChange({ ...ways, ...patch });
  return (
    <div className="flex flex-col gap-4">
      <Tick
        checked={ways.website}
        onChange={(v) => set({ website: v })}
        help="Get people to visit your website."
      >
        Website visits
      </Tick>
      {ways.website || type === "SEARCH" || type === "PERFORMANCE_MAX" ? (
        <Labelled label="Your business's website" className="sm:pl-7">
          <Input
            type="url"
            inputMode="url"
            value={ways.website_url}
            placeholder="https://www.example.com"
            onChange={(e) => set({ website_url: e.target.value })}
          />
        </Labelled>
      ) : null}
      <Tick
        checked={ways.calls}
        onChange={(v) => set({ calls: v })}
        help="Get people to call your business."
      >
        Phone calls
      </Tick>
      {ways.calls ? (
        <div className="grid gap-3 sm:grid-cols-[120px_1fr] sm:pl-7">
          <Labelled label="Country">
            <Input
              value={ways.phone_country}
              maxLength={2}
              placeholder="US"
              onChange={(e) => set({ phone_country: e.target.value.toUpperCase() })}
            />
          </Labelled>
          <Labelled label="Phone number" hint="Google checks the number belongs to your business.">
            <Input
              type="tel"
              value={ways.phone_number}
              placeholder="+1 416 555 0100"
              onChange={(e) => set({ phone_number: e.target.value })}
            />
          </Labelled>
        </div>
      ) : null}
      {type === "PERFORMANCE_MAX" ? (
        <Tick
          checked={ways.store_visits}
          onChange={(v) => set({ store_visits: v })}
          help="Show your store locations from your Google Business Profile."
        >
          Store visits
        </Tick>
      ) : null}
      <Tick
        checked={ways.app}
        onChange={(v) => set({ app: v })}
        help="Get people to download your app."
      >
        App downloads
      </Tick>
      {ways.app ? (
        <div className="grid gap-3 sm:grid-cols-[180px_1fr] sm:pl-7">
          <Labelled label="App store">
            <select
              value={ways.app_store}
              onChange={(e) => set({ app_store: e.target.value as Spec["ways"]["app_store"] })}
              className="border-pw-border-input bg-pw-card h-[46px] rounded-[12px] border px-3 text-[14px]"
            >
              <option value="GOOGLE_APP_STORE">Google Play</option>
              <option value="APPLE_APP_STORE">Apple App Store</option>
            </select>
          </Labelled>
          <Labelled
            label="App id"
            hint="The package name, such as com.example.app, or the App Store id."
          >
            <Input value={ways.app_id} onChange={(e) => set({ app_id: e.target.value })} />
          </Labelled>
        </div>
      ) : null}
      <Tick
        checked={ways.lead_forms}
        onChange={(v) => set({ lead_forms: v })}
        help="Collect leads with a form shown right in your ad."
      >
        Lead form submissions
      </Tick>
    </div>
  );
}
