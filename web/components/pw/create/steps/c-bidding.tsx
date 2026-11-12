"use client";

import { useState, type ReactNode } from "react";
import type { Spec } from "@/lib/creation";
import type { StepProps } from "../editor";
import { Card, Choice, Labelled, Note, NumberBox, Problems, Tick, money } from "../kit";
import { Act, DIRECT_LABEL, Select, directOf, type Direct } from "./a-parts";
import { BudgetCard } from "./c-budget";
import { APP_FOCUS_LABEL, moreStrategySentence } from "./c-words";

/*
  "Bidding and budget" for Demand Gen, Display, Shopping and App, as each of
  Google's flows offers it. Demand Gen focuses on conversions, conversion
  value or clicks, with Target CPC only for clicks. Display adds Manual CPC
  through "Or, select a bid strategy directly". Shopping bids for clicks or
  conversion value, or by hand. App asks its own question: installs, in-app
  actions or in-app action value. The budget sits under the bidding, since
  none of these types has a budget step.
*/

type Bidding = Spec["bidding"];
type Focus = Bidding["focus"];
type App = Spec["app"];

const FOCUS_LABEL: Record<Focus, string> = {
  conversions: "Conversions",
  conversion_value: "Conversion value",
  clicks: "Clicks",
  impression_share: "Impression share",
};

const FOCUS_HELP: Record<Focus, string> = {
  conversions: "Google bids to get as many conversions as it can within your budget.",
  conversion_value: "Google bids to get the most conversion value it can within your budget.",
  clicks: "Google bids to get as many clicks as it can within your budget.",
  impression_share: "",
};

const DIRECT_HELP: Partial<Record<Direct, string>> = {
  target_cpa: "As many conversions as possible at the cost per action you set.",
  target_roas: "As much conversion value as possible at the return on ad spend you set.",
  max_conversions: "As many conversions as possible within your budget.",
  max_value: "As much conversion value as possible within your budget.",
  max_clicks: "As many clicks as possible within your budget.",
  manual_cpc:
    "You set the most you'll pay for a click in each ad group. Google does not change it.",
};

export function MoreBidding({
  spec,
  setup,
  change,
  problems,
  extra,
}: StepProps & {
  /** Customer acquisition, which the Search bidding step draws, for Shopping. */
  extra?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-5">
      <Problems items={problems} />
      {spec.type === "APP" ? (
        <AppBidding spec={spec} setup={setup} change={change} />
      ) : (
        <FocusBidding spec={spec} setup={setup} change={change} />
      )}
      {extra}
      <BudgetCard spec={spec} change={change} />
    </div>
  );
}

function FocusBidding({ spec, setup, change }: Pick<StepProps, "spec" | "setup" | "change">) {
  const b = spec.bidding;
  const type = spec.type;
  const dg = spec.demand_gen;
  const cur = spec.currency;
  const set = (patch: Partial<Bidding>) => change("bidding", { ...b, ...patch });
  // Demand Gen has no manual CPC; a draft that somehow holds it is flagged by the server.
  const manual = b.strategy === "manual_cpc" && type !== "DEMAND_GEN";
  const focuses: Focus[] =
    type === "SHOPPING"
      ? ["clicks", "conversion_value"]
      : ["conversions", "conversion_value", "clicks"];
  const directs: Direct[] =
    type === "DISPLAY"
      ? ["target_cpa", "target_roas", "max_conversions", "max_value", "max_clicks", "manual_cpc"]
      : type === "SHOPPING"
        ? ["max_clicks", "target_roas", "max_value", "manual_cpc"]
        : [];
  const [direct, setDirect] = useState(manual);
  // These can be ticked before an amount is typed.
  const [cpcLimit, setCpcLimit] = useState(b.max_cpc !== null);
  const [cpcTarget, setCpcTarget] = useState(dg.target_cpc !== null);
  const conversionFocus = !manual && (b.focus === "conversions" || b.focus === "conversion_value");
  const noTracking = Boolean(setup.conversion && !setup.conversion.tracking);

  // A different focus keeps any target typed earlier, ticked again if it was set.
  const pickFocus = (focus: Focus) =>
    set({
      focus,
      strategy: "",
      set_target:
        focus === "conversions"
          ? b.target_cpa !== null
          : focus === "conversion_value"
            ? b.target_roas !== null
            : false,
    });

  const pickDirect = (d: Direct) => {
    if (d === "target_cpa") set({ focus: "conversions", set_target: true, strategy: "" });
    else if (d === "max_conversions")
      set({ focus: "conversions", set_target: false, strategy: "" });
    else if (d === "target_roas")
      set({ focus: "conversion_value", set_target: true, strategy: "" });
    else if (d === "max_value") set({ focus: "conversion_value", set_target: false, strategy: "" });
    else if (d === "max_clicks") set({ focus: "clicks", strategy: "" });
    // Manual CPC is bidding on clicks by hand; no focus question applies.
    else set({ focus: "clicks", strategy: "manual_cpc", set_target: false });
  };

  return (
    <>
      {noTracking && conversionFocus ? (
        <Note tone="warn">
          This account has no conversion tracking, so Google has nothing to count when it bids for
          conversions. {setup.conversion?.reason ? `${setup.conversion.reason} ` : ""}
          Set up conversion tracking in Google Ads first, or focus on clicks for now.
        </Note>
      ) : null}

      <Card title="Bidding">
        <div className="flex flex-col gap-5 p-6">
          {manual ? (
            <div className="flex flex-col gap-2">
              <p className="text-pw-ink text-[14px] leading-[20px]">
                You chose <strong>Manual CPC</strong> directly, so Google does not ask what to focus
                on.
              </p>
              <Act
                onClick={() => {
                  set({ strategy: "", focus: focuses[0], set_target: false });
                  setDirect(false);
                }}
              >
                Answer Google&apos;s question instead
              </Act>
            </div>
          ) : (
            <Labelled label="What do you want to focus on?">
              <Select
                aria-label="What do you want to focus on?"
                value={focuses.includes(b.focus) ? b.focus : ""}
                onChange={(e) => pickFocus(e.target.value as Focus)}
                className="w-full sm:w-[320px]"
              >
                {!focuses.includes(b.focus) ? <option value="">Choose a focus</option> : null}
                {focuses.map((f) => (
                  <option key={f} value={f}>
                    {FOCUS_LABEL[f]}
                  </option>
                ))}
              </Select>
              {focuses.includes(b.focus) ? (
                <span className="text-pw-ink-500 text-[13px] leading-[18px]">
                  {FOCUS_HELP[b.focus]}
                </span>
              ) : null}
            </Labelled>
          )}

          {!manual && b.focus === "conversions" && focuses.includes("conversions") ? (
            <div className="flex flex-col gap-3">
              <Tick
                checked={b.set_target}
                onChange={(v) => set({ set_target: v })}
                help="Google aims for about this cost for each conversion. Leave it unticked to get as many conversions as the budget allows."
              >
                Set a target cost per action (optional)
              </Tick>
              {b.set_target ? (
                <Labelled label="Target CPA" className="sm:w-[240px] sm:pl-7">
                  <NumberBox
                    value={b.target_cpa}
                    onChange={(v) => set({ target_cpa: v })}
                    unit={cur}
                    min={0.01}
                    placeholder="30.00"
                    ariaLabel="Target cost per action"
                  />
                </Labelled>
              ) : null}
            </div>
          ) : null}

          {!manual && b.focus === "conversion_value" ? (
            <div className="flex flex-col gap-3">
              <Tick
                checked={b.set_target}
                onChange={(v) => set({ set_target: v })}
                help="Google aims for this much conversion value for every amount spent. Leave it unticked to get the most value the budget allows."
              >
                Set a target return on ad spend (optional)
              </Tick>
              {b.set_target ? (
                <Labelled
                  label="Target ROAS"
                  className="sm:w-[240px] sm:pl-7"
                  hint={`400% means ${money(4, cur)} in conversion value for every ${money(1, cur)} spent.`}
                >
                  <NumberBox
                    value={b.target_roas}
                    onChange={(v) => set({ target_roas: v })}
                    unit="%"
                    min={1}
                    placeholder="400"
                    ariaLabel="Target return on ad spend, in percent"
                  />
                </Labelled>
              ) : null}
            </div>
          ) : null}

          {!manual && b.focus === "clicks" && type === "DEMAND_GEN" ? (
            <div className="flex flex-col gap-3">
              <Tick
                checked={cpcTarget}
                onChange={(v) => {
                  setCpcTarget(v);
                  if (!v) change("demand_gen", { ...dg, target_cpc: null });
                }}
                help="Google aims for about this average cost for each click. Leave it unticked to get as many clicks as the budget allows."
              >
                Set a target cost per click (optional)
              </Tick>
              {cpcTarget ? (
                <Labelled label="Target CPC" className="sm:w-[240px] sm:pl-7">
                  <NumberBox
                    value={dg.target_cpc}
                    onChange={(v) => change("demand_gen", { ...dg, target_cpc: v })}
                    unit={cur}
                    min={0.01}
                    placeholder="0.80"
                    ariaLabel="Target cost per click"
                  />
                </Labelled>
              ) : null}
            </div>
          ) : null}

          {!manual && b.focus === "clicks" && type !== "DEMAND_GEN" ? (
            <div className="flex flex-col gap-3">
              <Tick
                checked={cpcLimit}
                onChange={(v) => {
                  setCpcLimit(v);
                  if (!v) set({ max_cpc: null });
                }}
                help="The most Google may bid for any one click. A low limit can cost you clicks."
              >
                Set a maximum cost per click bid limit
              </Tick>
              {cpcLimit ? (
                <Labelled label="Maximum CPC bid limit" className="sm:w-[240px] sm:pl-7">
                  <NumberBox
                    value={b.max_cpc}
                    onChange={(v) => set({ max_cpc: v })}
                    unit={cur}
                    min={0.01}
                    placeholder="2.00"
                    ariaLabel="Maximum CPC bid limit"
                  />
                </Labelled>
              ) : null}
            </div>
          ) : null}

          {manual ? (
            <Labelled
              label="Default ad group bid"
              hint="The most you'll pay for a click. The ad group can have a bid of its own on the next step."
              className="sm:w-[240px]"
            >
              <NumberBox
                value={b.default_bid}
                onChange={(v) => set({ default_bid: v })}
                unit={cur}
                min={0.01}
                placeholder={type === "SHOPPING" ? "0.60" : "1.00"}
                ariaLabel="Default ad group bid"
              />
            </Labelled>
          ) : null}

          {directs.length ? (
            <div className="border-pw-border flex flex-col gap-3 border-t pt-5">
              <Act onClick={() => setDirect((d) => !d)}>
                {direct ? "Hide the bid strategies" : "Or, select a bid strategy directly"}
              </Act>
              {direct ? (
                <fieldset className="flex flex-col gap-3">
                  <legend className="sr-only">Bid strategy</legend>
                  {directs.map((d) => (
                    <Choice
                      key={d}
                      name="bid-strategy"
                      checked={directOf(b) === d}
                      onChange={() => pickDirect(d)}
                      help={DIRECT_HELP[d]}
                    >
                      {DIRECT_LABEL[d]}
                    </Choice>
                  ))}
                </fieldset>
              ) : null}
            </div>
          ) : null}

          <p className="bg-pw-muted text-pw-ink-700 rounded-[12px] px-4 py-3 text-[14px] leading-[20px]">
            <span className="text-pw-ink font-semibold">Your bid strategy. </span>
            {moreStrategySentence(spec)}
          </p>

          <p className="text-pw-ink-500 text-[13px] leading-[18px]">
            {type === "DEMAND_GEN"
              ? "Demand Gen has no manual CPC or impression share bidding. Google recommends a focus on conversions or conversion value once conversion tracking is set up."
              : type === "SHOPPING"
                ? "Shopping bids for clicks or conversion value, or with manual CPC. Google recommends conversion value when your sales carry values."
                : "Viewable CPM, which Display also offers, isn't available in PPCWay yet."}
          </p>
        </div>
      </Card>
    </>
  );
}

/*
  App bidding: "What do you want to focus on?" with an optional target under
  each answer. A target is sent only when it has an amount, so unticking
  clears it. Engagement campaigns bid for actions in the app, never
  installs; pre-registration bids for pre-registrations and asks nothing.
*/
function AppBidding({ spec, setup, change }: Pick<StepProps, "spec" | "setup" | "change">) {
  const app = spec.app;
  const currency = spec.currency;
  const set = (patch: Partial<App>) => change("app", { ...app, ...patch });
  const pre = app.subtype === "APP_CAMPAIGN_FOR_PRE_REGISTRATION";
  const engagement = app.subtype === "APP_CAMPAIGN_FOR_ENGAGEMENT";
  const focuses: App["focus"][] = engagement
    ? ["in_app_actions", "in_app_value"]
    : ["installs", "in_app_actions", "in_app_value"];
  const value = app.focus === "in_app_value";
  const [target, setTarget] = useState(value ? app.target_roas !== null : app.target_cpa !== null);

  const pickFocus = (focus: App["focus"]) => {
    // A cost per install is not a cost per action, so that amount is not carried across.
    const crossing =
      (focus === "installs" && app.focus === "in_app_actions") ||
      (focus === "in_app_actions" && app.focus === "installs");
    const cpa = crossing ? null : app.target_cpa;
    set({ focus, target_cpa: cpa });
    setTarget(focus === "in_app_value" ? app.target_roas !== null : cpa !== null);
  };
  const untick = () => {
    setTarget(false);
    set(value ? { target_roas: null } : { target_cpa: null });
  };

  const words: Record<App["focus"], { tick: string; label: string; help: string }> = {
    installs: {
      tick: "Set a target cost per install (optional)",
      label: "Target cost per install",
      help: "Google aims for about this average cost for each install. Leave it unticked to get as many installs as the budget allows.",
    },
    in_app_actions: {
      tick: "Set a target cost per action (optional)",
      label: "Target cost per action",
      help: "Google aims for about this average cost for each in-app action. Leave it unticked to get as many as the budget allows.",
    },
    in_app_value: {
      tick: "Set a target return on ad spend (optional)",
      label: "Target return on ad spend",
      help: "Google aims for this much in-app value for every amount spent. Leave it unticked to get the most value the budget allows.",
    },
  };
  const w = words[app.focus];

  return (
    <Card title="Bidding">
      <div className="flex flex-col gap-5 p-6">
        {pre ? (
          <p className="text-pw-ink text-[14px] leading-[20px]">
            A pre-registration campaign bids for pre-registrations, so Google does not ask what to
            focus on. It gets as many people to pre-register on Google Play as the budget allows.
          </p>
        ) : (
          <>
            <Labelled label="What do you want to focus on?">
              <Select
                aria-label="What do you want to focus on?"
                value={focuses.includes(app.focus) ? app.focus : ""}
                onChange={(e) => pickFocus(e.target.value as App["focus"])}
                className="w-full sm:w-[320px]"
              >
                {!focuses.includes(app.focus) ? <option value="">Choose a focus</option> : null}
                {focuses.map((f) => (
                  <option key={f} value={f}>
                    {APP_FOCUS_LABEL[f]}
                  </option>
                ))}
              </Select>
              {engagement ? (
                <span className="text-pw-ink-500 text-[13px] leading-[18px]">
                  An engagement campaign reaches people who already have the app, so it bids for
                  actions in the app rather than installs.
                </span>
              ) : null}
            </Labelled>

            {focuses.includes(app.focus) ? (
              <div className="flex flex-col gap-3">
                <Tick
                  checked={target}
                  onChange={(v) => (v ? setTarget(true) : untick())}
                  help={w.help}
                >
                  {w.tick}
                </Tick>
                {target ? (
                  <Labelled
                    label={w.label}
                    className="sm:w-[240px] sm:pl-7"
                    hint={
                      value
                        ? `400% means ${money(4, currency)} in value for every ${money(1, currency)} spent.`
                        : undefined
                    }
                  >
                    <NumberBox
                      value={value ? app.target_roas : app.target_cpa}
                      onChange={(v) => set(value ? { target_roas: v } : { target_cpa: v })}
                      unit={value ? "%" : currency}
                      min={value ? 1 : 0.01}
                      placeholder={value ? "300" : app.focus === "installs" ? "2.00" : "10.00"}
                      ariaLabel={w.label}
                    />
                  </Labelled>
                ) : null}
              </div>
            ) : null}

            {app.focus !== "installs" ? (
              <InAppActions spec={spec} setup={setup} change={change} />
            ) : null}

            {app.focus !== "installs" ? (
              <Note>
                {value
                  ? "Bidding for in-app action value needs in-app purchases tracked with their values, through Google Analytics for Firebase or an app analytics partner."
                  : "Bidding for in-app actions needs those actions tracked as conversions, through Google Analytics for Firebase or an app analytics partner."}
              </Note>
            ) : null}
          </>
        )}

        {pre ? <InAppActions spec={spec} setup={setup} change={change} /> : null}

        <p className="bg-pw-muted text-pw-ink-700 rounded-[12px] px-4 py-3 text-[14px] leading-[20px]">
          <span className="text-pw-ink font-semibold">Your bid strategy. </span>
          {moreStrategySentence(spec)}
        </p>
        <p className="text-pw-ink-500 text-[13px] leading-[18px]">
          Google advises letting an App campaign reach about 100 conversions before changing its
          bids or budget, so its learning is not reset.
        </p>
      </div>
    </Card>
  );
}

/*
  "Select in-app actions to bid for": the account's app conversion actions,
  which Google bids towards for in-app actions, in-app value and
  pre-registration (`selective_optimization` on the campaign). Only actions
  from the app itself are offered first; the rest follow.
*/
function InAppActions({ spec, setup, change }: Pick<StepProps, "spec" | "setup" | "change">) {
  const app = spec.app;
  const actions = (setup.conversion?.goals ?? [])
    .flatMap((g) => g.actions.map((a) => ({ ...a, origin: g.origin, goal: g.label })))
    .filter((a) => a.resource && a.status === "ENABLED")
    .sort((a, b) => Number(b.origin === "APP") - Number(a.origin === "APP"));
  const chosen = new Set(app.conversion_actions);
  const toggle = (resource: string, on: boolean) => {
    const next = new Set(chosen);
    if (on) next.add(resource);
    else next.delete(resource);
    change("app", { ...app, conversion_actions: [...next] });
  };
  return (
    <Labelled
      label="Select in-app actions to bid for"
      hint="Google bids towards these actions only. Choose the ones that matter to your business."
    >
      {actions.length ? (
        <div className="flex flex-col gap-2">
          {actions.map((a) => (
            <Tick
              key={a.resource}
              checked={chosen.has(a.resource!)}
              onChange={(on) => toggle(a.resource!, on)}
              help={`${a.goal}${a.origin === "APP" ? ", from the app" : ""}`}
            >
              {a.name}
            </Tick>
          ))}
        </div>
      ) : (
        <Note tone="warn">
          This account has no conversion actions to bid for yet. Track your app&apos;s in-app
          actions in Google Ads (Goals, then Conversions) through Google Analytics for Firebase or
          an app analytics partner, then come back.
        </Note>
      )}
    </Labelled>
  );
}
