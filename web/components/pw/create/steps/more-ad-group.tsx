"use client";

import type { ReactNode } from "react";
import type { Spec } from "@/lib/creation";
import type { StepProps } from "../editor";
import {
  Card,
  Chips,
  Choice,
  Labelled,
  Note,
  NumberBox,
  Problems,
  Tick,
  Toggle,
  money,
} from "../kit";
import { locationsSummary } from "./a-locations";
import { Act, count } from "./a-parts";
import { Section, Text } from "./b-form";
import { AudienceSignal } from "./b-pmax";
import { SegmentsEditor } from "./c-targeting";
import { CHANNELS } from "./c-words";

/*
  The ad group step for Demand Gen, Display and Shopping. A new campaign
  gets one ad group here, as in Google's flows; more are added in Google Ads
  afterwards. Demand Gen: the channels the ads may show on, optimized
  targeting and audience segments. Display: optimized targeting, segments to
  add or exclude, and content keywords. Shopping: the name and, under
  manual CPC, the bid; its ads are built from the product feed.
*/

export function StepMoreAdGroup(props: StepProps) {
  if (props.spec.type === "DEMAND_GEN") return <DemandGenGroup {...props} />;
  if (props.spec.type === "DISPLAY") return <DisplayGroup {...props} />;
  if (props.spec.type === "SHOPPING") return <ShoppingGroup {...props} />;
  return null;
}

function NameCard({
  value,
  onChange,
  children,
}: {
  value: string;
  onChange: (next: string) => void;
  children?: ReactNode;
}) {
  return (
    <Card title="Ad group">
      <div className="flex flex-col gap-4 p-5 sm:p-6">
        <Text
          label="Ad group name"
          value={value}
          placeholder="Ad group 1"
          hint="Customers never see it."
          onChange={onChange}
        />
        {children}
      </div>
    </Card>
  );
}

/** The ad group's own bid under manual CPC, falling back to the bidding step's default. */
function BidBox({
  label,
  value,
  fallback,
  currency,
  onChange,
}: {
  label: string;
  value: number | null;
  fallback: number | null;
  currency: string;
  onChange: (next: number | null) => void;
}) {
  return (
    <Labelled
      label={label}
      hint={
        fallback
          ? `The most you'll pay for a click. Empty uses the default bid from the bidding step, ${money(fallback, currency)}.`
          : "The most you'll pay for a click. Set a default bid on the bidding step too."
      }
      className="sm:w-[300px]"
    >
      <NumberBox
        value={value}
        onChange={onChange}
        unit={currency}
        min={0.01}
        placeholder={fallback ? fallback.toFixed(2) : "1.00"}
        ariaLabel={label}
      />
    </Labelled>
  );
}

function DemandGenGroup({ spec, setup, change, problems, go }: StepProps) {
  const dg = spec.demand_gen;
  const set = (patch: Partial<Spec["demand_gen"]>) => change("demand_gen", { ...dg, ...patch });
  const chosen = dg.selected;
  const toggle = (id: string, on: boolean) =>
    set({
      selected: on ? [...chosen.filter((c) => c !== id), id] : chosen.filter((c) => c !== id),
    });
  const hasVideo = dg.ads.some((a) => a.format === "video");
  const onlyInStream =
    dg.channels === "choose" && chosen.length === 1 && chosen[0] === "youtube_in_stream";
  const languages = spec.languages.map((l) => l.name).join(", ") || "none chosen yet";

  return (
    <div className="flex flex-col gap-5">
      <Problems items={problems} />
      <NameCard value={dg.ad_group_name} onChange={(ad_group_name) => set({ ad_group_name })} />

      <Card title="Channels" help="Where this ad group's ads may show.">
        <fieldset className="flex flex-col gap-4 p-5 sm:p-6">
          <legend className="sr-only">Channels</legend>
          <Choice
            name="dg-channels"
            checked={dg.channels === "all"}
            onChange={() => set({ channels: "all" })}
            help="Google shows your ads where they're likely to do best: YouTube, Discover, Gmail, the Display Network and Maps."
          >
            All Google channels (recommended)
          </Choice>
          <Choice
            name="dg-channels"
            checked={dg.channels === "choose"}
            onChange={() => set({ channels: "choose" })}
            help="Pick the places your ads may show. Fewer channels usually means fewer results for the same budget."
          >
            Let me choose
          </Choice>
          {dg.channels === "choose" ? (
            <div className="flex flex-col gap-3 sm:pl-7">
              {CHANNELS.map((c) => {
                const on = chosen.includes(c.id);
                return (
                  <Tick
                    key={c.id}
                    checked={on}
                    // At least one channel stays on.
                    disabled={on && chosen.length === 1}
                    onChange={(v) => toggle(c.id, v)}
                    help={c.help}
                  >
                    {c.label}
                  </Tick>
                );
              })}
              {!chosen.length ? (
                <p className="text-pw-bad text-[13px]">Choose at least one channel.</p>
              ) : null}
              {onlyInStream && !hasVideo ? (
                <Note tone="warn">
                  YouTube in-stream shows video ads only, and this ad group has no video ad yet. Add
                  one on the next step, or choose more channels.
                </Note>
              ) : null}
            </div>
          ) : null}
        </fieldset>
      </Card>

      <Card title="Audience" help="Who Google looks for first.">
        <Section title="Optimized targeting">
          <Toggle
            on={dg.optimized_targeting}
            onChange={(optimized_targeting) => set({ optimized_targeting })}
            help="Google may show your ads to people beyond your audience segments when it expects them to convert. Google recommends keeping it on."
          >
            Optimized targeting
          </Toggle>
        </Section>
        <Section
          title="Audience segments"
          help="Optional. Your customer lists, website visitors, custom segments and Google's interests. Your own lists work best."
        >
          <AudienceSignal signal={dg.segments} onChange={(segments) => set({ segments })} />
          {dg.segments.length ? (
            <p className="text-pw-ink-400 text-[12px]">
              {count(dg.segments.length, "segment")} added.
            </p>
          ) : null}
        </Section>
        <Section title="Locations and languages">
          <p className="text-pw-ink-700 text-[14px] leading-[20px]">
            {`Places: ${locationsSummary(spec.locations, setup)}. Languages: ${languages}. `}
            {dg.campaign_level_targeting
              ? "They are set for the whole campaign, and this ad group uses them."
              : "Google keeps them on the ad group, its default for Demand Gen, and PPCWay gives this ad group the ones from Campaign settings."}
          </p>
          <Act onClick={() => go("settings")}>Change them in Campaign settings</Act>
        </Section>
      </Card>
    </div>
  );
}

function DisplayGroup({ spec, change, problems }: StepProps) {
  const d = spec.display;
  const set = (patch: Partial<Spec["display"]>) => change("display", { ...d, ...patch });
  const manual = spec.bidding.strategy === "manual_cpc";
  // Google asks for a segment or keyword before optimized targeting can go off.
  const signals = d.segments.length > 0 || d.keywords.length > 0;

  return (
    <div className="flex flex-col gap-5">
      <Problems items={problems} />
      <NameCard value={d.ad_group_name} onChange={(ad_group_name) => set({ ad_group_name })}>
        {manual ? (
          <BidBox
            label="Default bid"
            value={d.default_bid}
            fallback={spec.bidding.default_bid}
            currency={spec.currency}
            onChange={(default_bid) => set({ default_bid })}
          />
        ) : null}
      </NameCard>

      <Card title="Targeting" help="Who sees your ads, and on what kind of pages.">
        <Section title="Optimized targeting">
          <Toggle
            on={d.optimized_targeting}
            disabled={d.optimized_targeting && !signals}
            onChange={(optimized_targeting) => set({ optimized_targeting })}
            help={
              d.optimized_targeting && !signals
                ? "Google finds people likely to convert, starting from your landing page and assets. To turn it off, add an audience segment or a keyword first."
                : "Google finds people likely to convert, starting from your segments and keywords, and may go beyond them. Google recommends keeping it on."
            }
          >
            Optimized targeting
          </Toggle>
        </Section>
        <Section
          title="Audience segments"
          help="Optional. Add segments to reach, or exclude people you don't want to reach, such as existing customers."
        >
          <SegmentsEditor value={d.segments} onChange={(segments) => set({ segments })} />
        </Section>
        <Section
          title="Keywords"
          help="Optional. Content keywords tell Google what pages to look for: your ads show on sites, apps and videos about these words. Up to 200."
        >
          <Chips
            values={d.keywords}
            onChange={(keywords) => set({ keywords })}
            most={200}
            longest={80}
            placeholder="A word or phrase, such as: running shoes"
            ariaLabel="Add a keyword"
          />
          <p className="text-pw-ink-400 text-[12px]">
            {d.keywords.length} of 200.{" "}
            {d.optimized_targeting
              ? "With optimized targeting on, Google treats them as a starting point."
              : "Ads show only on pages about these words."}
          </p>
        </Section>
      </Card>
    </div>
  );
}

function ShoppingGroup({ spec, change, problems, go }: StepProps) {
  const sh = spec.shopping;
  const set = (patch: Partial<Spec["shopping"]>) => change("shopping", { ...sh, ...patch });
  const manual = spec.bidding.strategy === "manual_cpc";

  return (
    <div className="flex flex-col gap-5">
      <Problems items={problems} />
      <NameCard value={sh.ad_group_name} onChange={(ad_group_name) => set({ ad_group_name })}>
        {manual ? (
          <BidBox
            label="Bid"
            value={sh.default_bid}
            fallback={spec.bidding.default_bid}
            currency={spec.currency}
            onChange={(default_bid) => set({ default_bid })}
          />
        ) : null}
      </NameCard>

      <Card title="Products" help="What this ad group advertises.">
        <div className="flex flex-col gap-3 p-5 sm:p-6">
          <p className="text-pw-ink-700 text-[14px] leading-[20px]">
            {`The ad group starts with one product group, All products, which covers every product in ${sh.merchant_id ? `Merchant Center account ${sh.merchant_id}` : "your Merchant Center account"}${sh.feed_label.trim() ? ` with the feed label "${sh.feed_label.trim()}"` : ""}.`}
          </p>
          <p className="text-pw-ink-700 text-[14px] leading-[20px]">
            There is no ad to write. Google builds each product ad from your product data: its
            title, image, price and your store&apos;s name.
          </p>
          <p className="text-pw-ink-500 text-[13px] leading-[18px]">
            After publishing you can split the product group in Google Ads, by brand, category or
            item ID, and give each part its own bid.
          </p>
          {!sh.merchant_id ? (
            <Act onClick={() => go("settings")}>Choose the Merchant Center account</Act>
          ) : null}
        </div>
      </Card>
    </div>
  );
}
