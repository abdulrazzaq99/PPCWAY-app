"use client";

import Link from "next/link";
import { useState } from "react";
import type { Spec } from "@/lib/creation";
import type { StepProps } from "../editor";
import { Card, Choice, Labelled, Note, NumberBox, Problems, Tick, Toggle, money } from "../kit";
import {
  Act,
  DIRECT_LABEL,
  Select,
  WHERE_LABEL,
  directOf,
  strategySentence,
  type Direct,
} from "./a-parts";
import { MoreBidding } from "./c-bidding";
import { isMore } from "./c-words";

/*
  Google's bidding step: "What do you want to focus on?", an optional target
  under it, and for those who know what they want, "Or, select a bid strategy
  directly". Performance Max only bids for conversions or conversion value.
  Enhanced CPC is not offered: Google retired it for Search in March 2025,
  and manual CPC here is plain manual CPC. Customer acquisition sits on this
  step in Google's flow too, though Google takes it only once the campaign
  exists, so PPCWay sets it straight after publishing.
*/

type Bidding = Spec["bidding"];
type Focus = Bidding["focus"];

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
  impression_share:
    "Google bids to show your ad on the share of searches you choose, where you choose on the page.",
};

const DIRECT_HELP: Record<Direct, string> = {
  target_cpa: "As many conversions as possible at the cost per action you set.",
  target_roas: "As much conversion value as possible at the return on ad spend you set.",
  max_conversions: "As many conversions as possible within your budget.",
  max_value: "As much conversion value as possible within your budget.",
  max_clicks: "As many clicks as possible within your budget.",
  impression_share:
    "Your ad shown on a share of searches you choose, at the place on the page you choose.",
  manual_cpc:
    "You set the most you'll pay for a click in each ad group. Google does not change it.",
};

const SEARCH_ONLY: Direct[] = ["max_clicks", "impression_share", "manual_cpc"];

export function StepBidding(props: StepProps) {
  const { spec, change } = props;
  if (!isMore(spec.type)) return <SearchBidding {...props} />;
  // Demand Gen, Display, Shopping and App: bidding and budget on one step, in their own words.
  const b = spec.bidding;
  const set = (patch: Partial<Bidding>) => change("bidding", { ...b, ...patch });
  // Google's Shopping flow keeps customer acquisition with bidding, as Search does.
  const acquisition =
    spec.type === "SHOPPING" &&
    ((b.strategy !== "manual_cpc" && b.focus === "conversion_value") || b.new_customers !== "off");
  return (
    <MoreBidding
      {...props}
      extra={acquisition ? <CustomerAcquisition b={b} set={set} currency={spec.currency} /> : null}
    />
  );
}

function SearchBidding({ spec, setup, change, problems, go }: StepProps) {
  const b = spec.bidding;
  const search = spec.type === "SEARCH";
  const set = (patch: Partial<Bidding>) => change("bidding", { ...b, ...patch });
  const cur = spec.currency;
  const manual = b.strategy === "manual_cpc";
  const conversionFocus = !manual && (b.focus === "conversions" || b.focus === "conversion_value");
  const [direct, setDirect] = useState(manual);
  // "Set a maximum cost per click bid limit" can be ticked before an amount is typed.
  const [cpcLimit, setCpcLimit] = useState(b.max_cpc !== null);

  const focuses: Focus[] = search
    ? ["conversions", "conversion_value", "clicks", "impression_share"]
    : ["conversions", "conversion_value"];
  const directs = (Object.keys(DIRECT_LABEL) as Direct[]).filter(
    (d) => search || !SEARCH_ONLY.includes(d),
  );

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
    else if (d === "impression_share") set({ focus: "impression_share", strategy: "" });
    // Manual CPC is bidding on clicks by hand; no focus question applies.
    else set({ focus: "clicks", strategy: "manual_cpc", set_target: false });
  };

  const noTracking = Boolean(setup.conversion && !setup.conversion.tracking);
  const aiMaxClash = search && manual && spec.ai_max.enabled && spec.ai_max.search_term_matching;

  return (
    <div className="flex flex-col gap-5">
      <Problems items={problems} />

      {noTracking && (conversionFocus || !search) ? (
        <Note tone="warn">
          This account has no conversion tracking, so Google has nothing to count when it bids for
          conversions. {setup.conversion?.reason ? `${setup.conversion.reason} ` : ""}
          <Link href="/conversions/new" className="font-semibold underline">
            Set up conversion tracking
          </Link>{" "}
          first
          {search ? ", or focus on clicks for now." : ". Performance Max needs it."}
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
                  set({ strategy: "", focus: "conversions", set_target: b.target_cpa !== null });
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

          {!manual && b.focus === "conversions" ? (
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
                <div className="flex flex-col gap-4 sm:pl-7">
                  <Labelled
                    label="Target ROAS"
                    className="sm:w-[240px]"
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
                  {search ? (
                    <div className="flex flex-col gap-3">
                      <Toggle
                        on={b.explore}
                        onChange={(v) => set({ explore: v })}
                        help="Smart Bidding Exploration lets return on ad spend dip below your target to reach searches you'd otherwise miss. Google suggests running it for at least 6 weeks; it does little when the budget is the limit."
                      >
                        Allow Smart Bidding to explore new traffic
                      </Toggle>
                      {b.explore ? (
                        <Labelled
                          label="Target ROAS tolerance"
                          hint="How far below your target Google may go while exploring."
                          className="sm:w-[240px] sm:pl-[50px]"
                        >
                          <Select
                            aria-label="Target ROAS tolerance"
                            value={b.explore_tolerance}
                            onChange={(e) => set({ explore_tolerance: Number(e.target.value) })}
                          >
                            {[...new Set([10, 15, 20, 25, 30, b.explore_tolerance])]
                              .filter((n) => n >= 10 && n <= 30)
                              .sort((x, y) => x - y)
                              .map((n) => (
                                <option key={n} value={n}>
                                  {n}% below target
                                </option>
                              ))}
                          </Select>
                        </Labelled>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}

          {!manual && b.focus === "clicks" && search ? (
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

          {!manual && b.focus === "impression_share" && search ? (
            <div className="grid gap-4 sm:grid-cols-3">
              <Labelled label="Where do you want your ads to appear">
                <Select
                  aria-label="Where do you want your ads to appear"
                  value={b.impression_location}
                  onChange={(e) =>
                    set({ impression_location: e.target.value as Bidding["impression_location"] })
                  }
                >
                  {(Object.keys(WHERE_LABEL) as Bidding["impression_location"][]).map((w) => (
                    <option key={w} value={w}>
                      {WHERE_LABEL[w]}
                    </option>
                  ))}
                </Select>
              </Labelled>
              <Labelled label="Percent (%) impression share to target">
                <NumberBox
                  value={b.impression_percent}
                  onChange={(v) => set({ impression_percent: v })}
                  unit="%"
                  min={1}
                  max={100}
                  placeholder="80"
                  ariaLabel="Percent impression share to target"
                />
              </Labelled>
              <Labelled label="Maximum CPC bid limit" hint="Google needs one for this strategy.">
                <NumberBox
                  value={b.impression_max_cpc}
                  onChange={(v) => set({ impression_max_cpc: v })}
                  unit={cur}
                  min={0.01}
                  placeholder="3.00"
                  ariaLabel="Maximum CPC bid limit"
                />
              </Labelled>
              <p className="text-pw-ink-500 text-[13px] leading-[18px] sm:col-span-3">
                Impression share counts Google Search only, not search partners. A low bid limit can
                stop Google reaching the share you ask for.
              </p>
            </div>
          ) : null}

          {manual ? (
            <Labelled
              label="Default ad group bid"
              hint="The most you'll pay for a click, used by every ad group that has no bid of its own."
              className="sm:w-[240px]"
            >
              <NumberBox
                value={b.default_bid}
                onChange={(v) => set({ default_bid: v })}
                unit={cur}
                min={0.01}
                placeholder="1.50"
                ariaLabel="Default ad group bid"
              />
            </Labelled>
          ) : null}

          {aiMaxClash ? (
            <Note tone="warn">
              AI Max search term matching will not work with manual CPC bidding. Choose another bid
              strategy, or turn search term matching off.{" "}
              <button
                type="button"
                onClick={() => go("ai_max")}
                className="font-semibold underline"
              >
                Go to AI Max
              </button>
            </Note>
          ) : null}

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
                {search ? (
                  <Note>
                    Enhanced CPC is no longer available for Search campaigns. Google retired it in
                    March 2025, so it is not offered here.
                  </Note>
                ) : null}
              </fieldset>
            ) : null}
          </div>

          <p className="bg-pw-muted text-pw-ink-700 rounded-[12px] px-4 py-3 text-[14px] leading-[20px]">
            <span className="text-pw-ink font-semibold">Your bid strategy. </span>
            {strategySentence(spec)}
          </p>

          {!search ? (
            <p className="text-pw-ink-500 text-[13px] leading-[18px]">
              Google recommends a focus on conversion value when your conversions carry values.
            </p>
          ) : null}
        </div>
      </Card>

      {conversionFocus || b.new_customers !== "off" ? (
        <CustomerAcquisition b={b} set={set} currency={cur} />
      ) : null}
    </div>
  );
}

/*
  Customer acquisition. Bidding higher needs a focus on conversion value;
  bidding only for new customers works with either conversion focus. Google
  takes the setting through its goals service once the campaign exists, so
  it is sent right after publishing, and said if Google turns it down.
*/
function CustomerAcquisition({
  b,
  set,
  currency,
}: {
  b: Bidding;
  set: (patch: Partial<Bidding>) => void;
  currency: string;
}) {
  return (
    <Card
      title="Customer acquisition"
      help="Choose how Google bids for people who haven't bought from you before."
    >
      <fieldset className="flex flex-col gap-4 p-6">
        <legend className="sr-only">Customer acquisition</legend>
        <Choice
          name="new-customers"
          checked={b.new_customers === "off"}
          onChange={() => set({ new_customers: "off" })}
          help="Google's default."
        >
          Bid equally for new and existing customers
        </Choice>
        <Choice
          name="new-customers"
          checked={b.new_customers === "bid_higher"}
          onChange={() => set({ new_customers: "bid_higher" })}
          help="Google adds the value you set to each sale from a new customer. Needs a focus on conversion value."
        >
          Bid higher for new customers than for existing customers
        </Choice>
        {b.new_customers === "bid_higher" ? (
          <Labelled
            label="Value of a new customer"
            hint="What a new customer is worth to you beyond the sale itself."
            className="sm:w-[240px] sm:pl-7"
          >
            <NumberBox
              value={b.new_customer_value}
              onChange={(v) => set({ new_customer_value: v })}
              unit={currency}
              min={0}
              placeholder="25.00"
              ariaLabel="Value of a new customer"
            />
          </Labelled>
        ) : null}
        <Choice
          name="new-customers"
          checked={b.new_customers === "only"}
          onChange={() => set({ new_customers: "only" })}
          help="Ads show only to people Google sees as new customers. Works with a focus on conversions or conversion value."
        >
          Only bid for new customers
        </Choice>
        <p className="text-pw-ink-500 text-[13px] leading-[18px]">
          Google tells new customers apart using your customer lists, your website tag, or its own
          detection of purchases. It takes this setting only once the campaign exists, so PPCWay
          sets it straight after publishing and tells you if Google turns it down.
        </p>
      </fieldset>
    </Card>
  );
}
